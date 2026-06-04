from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user
from sqlalchemy import func, case, extract, desc
from datetime import datetime, timedelta, date
from app.database import db, Psicologo, Paciente, Cita, Usuario
import io
import csv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import calendar

# Crear Blueprint para APIs de estadísticas
stats_api = Blueprint('stats_api', __name__)

# Función auxiliar para calcular rangos de fechas
def get_date_range(periodo):
    """
    Obtiene el rango de fechas basado en el período seleccionado
    """
    today = datetime.now()
    
    if periodo == 'semana':
        # Esta semana (definir semana como desde el lunes previo al domingo siguiente)
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Fin de la semana (domingo a las 23:59:59)
        end_of_week = start_of_week + timedelta(days=6)
        end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Si una cita está programada para la próxima semana pero dentro del rango visible
        # del calendario (hasta 2 semanas), inclúyela también
        visible_range_end = end_of_week + timedelta(days=7)
        
        return start_of_week, visible_range_end
    
    elif periodo == 'mes':
        # Este mes
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0)
        # Último día del mes actual
        next_month = today.replace(day=28) + timedelta(days=4)
        last_day = (next_month - timedelta(days=next_month.day)).day
        end_of_month = today.replace(day=last_day, hour=23, minute=59, second=59)
        return start_of_month, end_of_month
    
    elif periodo == 'trimestre':
        # Este trimestre
        current_quarter = (today.month - 1) // 3 + 1
        start_month = (current_quarter - 1) * 3 + 1
        end_month = current_quarter * 3
        
        start_of_quarter = today.replace(month=start_month, day=1, hour=0, minute=0, second=0)
        
        # Último día del trimestre
        if end_month == 12:
            end_of_quarter = today.replace(month=end_month, day=31, hour=23, minute=59, second=59)
        else:
            end_of_quarter = today.replace(month=end_month + 1, day=1, hour=0, minute=0, second=0) - timedelta(seconds=1)
        
        return start_of_quarter, end_of_quarter
    
    elif periodo == 'año':
        # Este año
        start_of_year = today.replace(month=1, day=1, hour=0, minute=0, second=0)
        end_of_year = today.replace(month=12, day=31, hour=23, minute=59, second=59)
        return start_of_year, end_of_year
    
    else:  # 'todo' o cualquier otro valor
        # Sin límite de tiempo (solo aplica a los usuarios activos)
        return None, None

# API para obtener datos estadísticos
@stats_api.route('/estadisticas')
@login_required
def get_estadisticas():
    """
    Obtiene las estadísticas del sistema según el período seleccionado
    """
    periodo = request.args.get('periodo', 'semana')
    psicologo_id = current_user.id
    
    # Obtener rango de fechas para el filtro
    fecha_inicio, fecha_fin = get_date_range(periodo)
    
    # Consulta base para filtrar por psicólogo y rango de fechas
    pacientes_base_query = Paciente.query.filter_by(psicologo_id=psicologo_id)
    citas_query = Cita.query.filter_by(psicologo_id=psicologo_id)
    
    if fecha_inicio and fecha_fin:
        # Filtrar citas por fecha
        citas_query = citas_query.filter(Cita.fecha.between(fecha_inicio, fecha_fin))
    
    # 1. Total de pacientes
    pacientes_query = Paciente.query.join(
        Usuario, 
        Paciente.usuario_id == Usuario.id
    ).filter(
        Paciente.psicologo_id == psicologo_id,
        Usuario.activo == True
    )
    
    if fecha_inicio and fecha_fin:
        pacientes_query = pacientes_query.filter(Usuario.fecha_registro.between(fecha_inicio, fecha_fin))
    
    total_pacientes = pacientes_query.count()
    
    # 2. Estadísticas de citas
    total_citas = citas_query.count()
    citas_completadas = citas_query.filter_by(status='Completada').count()
    citas_pendientes = citas_query.filter_by(status='Programada').count()
    citas_canceladas = citas_query.filter_by(status='Cancelada').count()
    citas_reprogramadas = citas_query.filter_by(status='Reprogramada').count()
    
    # 3. Tasa de asistencia (porcentaje de citas completadas sobre el total de citas que no están pendientes)
    citas_no_pendientes = citas_completadas + citas_canceladas
    tasa_asistencia = round((citas_completadas / citas_no_pendientes * 100) if citas_no_pendientes > 0 else 0)
    
    # 4. Citas por mes
    if fecha_inicio and fecha_fin and fecha_inicio.year == fecha_fin.year:
        # Si estamos filtrando por un período dentro del mismo año
        citas_por_mes_query = db.session.query(
            extract('month', Cita.fecha).label('mes'),
            func.count(Cita.id).label('cantidad')
        ).filter(
            Cita.psicologo_id == psicologo_id,
            Cita.fecha.between(fecha_inicio, fecha_fin)
        ).group_by(extract('month', Cita.fecha)).all()
        
        # Crear un diccionario con todos los meses y valores en 0
        citas_por_mes = {i: 0 for i in range(1, 13)}
        
        # Llenar con los datos de la consulta
        for mes, cantidad in citas_por_mes_query:
            citas_por_mes[int(mes)] = cantidad
        
        # Convertir números de mes a nombres abreviados
        nombres_meses = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        citas_por_mes = {nombres_meses[mes]: cantidad for mes, cantidad in citas_por_mes.items()}
    else:
        # Si estamos viendo datos de varios años, agrupar por año y mes
        citas_por_mes_query = db.session.query(
            extract('year', Cita.fecha).label('anio'),
            extract('month', Cita.fecha).label('mes'),
            func.count(Cita.id).label('cantidad')
        ).filter(
            Cita.psicologo_id == psicologo_id
        )
        
        if fecha_inicio and fecha_fin:
            citas_por_mes_query = citas_por_mes_query.filter(Cita.fecha.between(fecha_inicio, fecha_fin))
        
        citas_por_mes_query = citas_por_mes_query.group_by(
            extract('year', Cita.fecha),
            extract('month', Cita.fecha)
        ).order_by(
            extract('year', Cita.fecha),
            extract('month', Cita.fecha)
        ).all()
        
        citas_por_mes = {}
        for anio, mes, cantidad in citas_por_mes_query:
            nombre_mes = f"{calendar.month_abbr[int(mes)]}-{int(anio)}"
            citas_por_mes[nombre_mes] = cantidad
    
    # 5. Pacientes por género
    pacientes_por_genero_query = db.session.query(
        Paciente.genero,
        func.count(Paciente.id).label('cantidad')
    ).join(
        Usuario, 
        Paciente.usuario_id == Usuario.id
    ).filter(
        Paciente.psicologo_id == psicologo_id,
        Usuario.activo == True
    )
    
    if fecha_inicio and fecha_fin:
        pacientes_por_genero_query = pacientes_por_genero_query.filter(
            Usuario.fecha_registro.between(fecha_inicio, fecha_fin)
        )
    
    pacientes_por_genero_query = pacientes_por_genero_query.group_by(Paciente.genero).all()
    
    pacientes_por_genero = {
        'masculino': 0,
        'femenino': 0,
        'otro': 0
    }
    
    for genero, cantidad in pacientes_por_genero_query:
        if genero and genero.lower() in ['masculino', 'hombre', 'm']:
            pacientes_por_genero['masculino'] += cantidad
        elif genero and genero.lower() in ['femenino', 'mujer', 'f']:
            pacientes_por_genero['femenino'] += cantidad
        else:
            pacientes_por_genero['otro'] += cantidad
    
    # 6. Pacientes por edad
    today = date.today()
    
    pacientes_por_edad = {
        '0-18': 0,
        '19-30': 0,
        '31-45': 0,
        '46-60': 0,
        '60+': 0
    }
    
    pacientes_edad_query = Paciente.query.join(
        Usuario, 
        Paciente.usuario_id == Usuario.id
    ).filter(
        Paciente.psicologo_id == psicologo_id, 
        Usuario.activo == True
    )
    
    if fecha_inicio and fecha_fin:
        pacientes_edad_query = pacientes_edad_query.filter(
            Usuario.fecha_registro.between(fecha_inicio, fecha_fin)
        )
    
    for paciente in pacientes_edad_query.all():
        if paciente.fecha_nacimiento:
            edad = today.year - paciente.fecha_nacimiento.year - (
                (today.month, today.day) < (paciente.fecha_nacimiento.month, paciente.fecha_nacimiento.day)
            )
            
            if edad <= 18:
                pacientes_por_edad['0-18'] += 1
            elif edad <= 30:
                pacientes_por_edad['19-30'] += 1
            elif edad <= 45:
                pacientes_por_edad['31-45'] += 1
            elif edad <= 60:
                pacientes_por_edad['46-60'] += 1
            else:
                pacientes_por_edad['60+'] += 1
    
    # 7. Últimas citas
    ultimas_citas_query = Cita.query.filter_by(psicologo_id=psicologo_id)
    
    if fecha_inicio and fecha_fin:
        ultimas_citas_query = ultimas_citas_query.filter(Cita.fecha.between(fecha_inicio, fecha_fin))
    
    ultimas_citas = ultimas_citas_query.order_by(desc(Cita.fecha)).limit(10).all()
    
    # Formatear las últimas citas para la respuesta
    ultimas_citas_formateadas = []
    for cita in ultimas_citas:
        paciente = Paciente.query.get(cita.paciente_id)
        ultimas_citas_formateadas.append({
            'id': cita.id,
            'paciente': f"{paciente.nombre} {paciente.apellido}" if paciente else "Paciente desconocido",
            'fecha': cita.fecha.isoformat(),
            'tipo': cita.tipo,
            'duracion': cita.duracion,
            'status': cita.status
        })
    
    # Construir el objeto de respuesta JSON
    resultado = {
        'pacientes': {
            'total': total_pacientes,
            'porGenero': pacientes_por_genero,
            'porEdad': pacientes_por_edad
        },
        'citas': {
            'total': total_citas,
            'completadas': citas_completadas,
            'pendientes': citas_pendientes,
            'canceladas': citas_canceladas,
            'reprogramadas': citas_reprogramadas,
            'asistencia': tasa_asistencia,
            'porMes': citas_por_mes,
            'porStatus': {
                'programadas': citas_pendientes,
                'completadas': citas_completadas,
                'reprogramadas': citas_reprogramadas,
                'canceladas': citas_canceladas
            },
            'ultimas': ultimas_citas_formateadas
        }
    }
    
    return jsonify(resultado)




# API para exportar estadísticas en PDF
@stats_api.route('/estadisticas/exportar', methods=['POST'])
@login_required
def exportar_estadisticas():
    """
    Exporta las estadísticas a un archivo PDF (versión extremadamente simplificada)
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    import io
    from datetime import datetime
    
    try:
        periodo = request.args.get('periodo', 'semana')
        psicologo_id = current_user.id
        
        # Crear un buffer para el PDF
        buffer = io.BytesIO()
        
        # Crear un PDF extremadamente básico
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            leftMargin=72,  # 1 pulgada
            rightMargin=72, 
            topMargin=72, 
            bottomMargin=72
        )
        
        # Usar solo estilos estándar
        styles = getSampleStyleSheet()
        
        # Contenido mínimo
        contenido = []
        
        # Solo texto simple
        contenido.append(Paragraph("Estadísticas de PsychCalendar", styles["Title"]))
        contenido.append(Spacer(1, 0.5*inch))
        contenido.append(Paragraph(f"Informe generado el {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))
        contenido.append(Spacer(1, 0.25*inch))
        contenido.append(Paragraph("Este es un informe de prueba para diagnosticar problemas con la generación de PDF.", styles["Normal"]))
        
        # Construir el PDF
        doc.build(contenido)
        
        # Preparar el archivo para su descarga
        buffer.seek(0)
        
        response = send_file(
            buffer,
            as_attachment=True,
            download_name=f"test_pdf_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf",
            mimetype='application/pdf'
        )
        
        # Añadir cabeceras importantes
        response.headers["Content-Disposition"] = f"attachment; filename=test_pdf_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error al generar PDF: {str(e)}\nDetalles: {error_details}")
        return jsonify({"success": False, "error": f"Error al generar el archivo PDF: {str(e)}"}), 500
    finally:
        if 'buffer' in locals():
            buffer.close()




@stats_api.route('/estadisticas/exportar/weasy', methods=['POST'])
@login_required
def exportar_estadisticas_weasy():
    """
    Exporta las estadísticas a un archivo PDF usando WeasyPrint
    (Para implementar esta función, necesitarás instalar: pip install weasyprint)
    """
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        import tempfile
        
        periodo = request.args.get('periodo', 'semana')
        psicologo_id = current_user.id
        
        # Fecha actual en formato legible
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        # Crear HTML básico con bootstrap para el reporte
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Estadísticas PsychCalendar</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ text-align: center; color: #4e73df; }}
                .fecha {{ text-align: center; margin-bottom: 30px; }}
                .seccion {{ margin-top: 20px; }}
                h2 {{ color: #5a5c69; border-bottom: 1px solid #eaecf4; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                table, th, td {{ border: 1px solid #e3e6f0; }}
                th, td {{ padding: 12px; text-align: left; }}
                th {{ background-color: #f8f9fc; }}
                tr:nth-child(even) {{ background-color: #f8f9fc; }}
                .resumen {{ display: flex; justify-content: space-between; flex-wrap: wrap; }}
                .metrica {{ width: 45%; padding: 15px; margin-bottom: 15px; border-radius: 5px; background-color: #f8f9fc; }}
            </style>
        </head>
        <body>
            <h1>Estadísticas de PsychCalendar - {periodo.capitalize()}</h1>
            <p class="fecha">Generado el {fecha_actual}</p>
            
            <div class="seccion">
                <h2>Reporte Básico</h2>
                <p>Este es un informe de prueba para diagnosticar problemas con la generación de PDF.</p>
                <p>Si este PDF se visualiza correctamente, el problema está en la implementación con ReportLab.</p>
            </div>
        </body>
        </html>
        '''
        
        # Configuración de fuentes
        font_config = FontConfiguration()
        
        # Crear un archivo PDF a partir del HTML
        pdf = HTML(string=html_content).write_pdf(font_config=font_config)
        
        # Crear un buffer para la respuesta
        buffer = io.BytesIO(pdf)
        buffer.seek(0)
        
        # Enviar el archivo
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"estadisticas_weasy_{periodo}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )
        
    except ImportError:
        return jsonify({"success": False, "error": "WeasyPrint no está instalado. Instale con: pip install weasyprint"}), 500
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error al generar PDF con WeasyPrint: {str(e)}\nDetalles: {error_details}")
        return jsonify({"success": False, "error": f"Error al generar el archivo PDF: {str(e)}"}), 500