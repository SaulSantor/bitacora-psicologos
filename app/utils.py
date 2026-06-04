from flask import current_app
from flask_mail import Message
from app import mail
from app.database import db



def enviar_email_credenciales(email, password, nombre):
    """
    Envía un email con las credenciales de acceso
    """
    try:
        msg = Message(
            'Credenciales de Acceso',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"""
        Hola {nombre},

        Se ha creado una cuenta para ti en nuestra plataforma de gestión psicológica.

        Tus credenciales de acceso son:
        Email: {email}
        Contraseña temporal: {password}

        Por seguridad, te recomendamos cambiar tu contraseña al primer inicio de sesión.

        Saludos cordiales,
        Equipo de PsychCalendar
        """
        
        mail.send(msg)
        print(f"Email enviado exitosamente a {email}")
        return True
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")
        return False


def enviar_notificacion_contacto(contacto):

    try:
        msg = Message(
            subject=f'Nuevo mensaje de contacto: {contacto.asunto}',
            recipients=['psychcalendarventas@gmail.com'],  # Lista de emails de administradores
            body=f'''
            Se ha recibido un nuevo mensaje de contacto:
            
            Nombre: {contacto.nombre}
            Email: {contacto.email}
            Teléfono: {contacto.telefono}
            Asunto: {contacto.asunto}
            
            Mensaje:
            {contacto.mensaje}
            
            Fecha: {contacto.fecha_envio.strftime('%d/%m/%Y %H:%M')}
            IP: {contacto.ip_remitente}
            ''',
            html=f'''
            <h3>Nuevo mensaje de contacto</h3>
            <p><strong>Nombre:</strong> {contacto.nombre}</p>
            <p><strong>Email:</strong> {contacto.email}</p>
            <p><strong>Teléfono:</strong> {contacto.telefono}</p>
            <p><strong>Asunto:</strong> {contacto.asunto}</p>
            <p><strong>Mensaje:</strong><br>{contacto.mensaje.replace('\\n', '<br>')}</p>
            <p><strong>Fecha:</strong> {contacto.fecha_envio.strftime('%d/%m/%Y %H:%M')}</p>
            <hr>
            <p><small>IP: {contacto.ip_remitente}</small></p>
            '''
        )
        mail.send(msg)
        
        # También puedes enviar una confirmación al remitente
        send_confirmation = True
        if send_confirmation:
            confirmation = Message(
                subject=f'Hemos recibido tu mensaje - PsychCalendar',
                recipients=[contacto.email],
                body=f'''
                Estimado/a {contacto.nombre},
                
                Hemos recibido tu mensaje con el asunto "{contacto.asunto}".
                
                Te responderemos a la brevedad posible.
                
                Saludos cordiales,
                El equipo de PsychCalendar
                ''',
                html=f'''
                <h3>Gracias por contactarnos</h3>
                <p>Estimado/a {contacto.nombre},</p>
                <p>Hemos recibido tu mensaje con el asunto "<strong>{contacto.asunto}</strong>".</p>
                <p>Te responderemos a la brevedad posible.</p>
                <br>
                <p>Saludos cordiales,</p>
                <p><strong>El equipo de PsychCalendar</strong></p>
                '''
            )
            mail.send(confirmation)
            
        return True
        
    except Exception as e:
        print(f"Error al enviar email de contacto: {str(e)}")
        # Podrías loggear el error para análisis posterior
        return False



def enviar_respuesta_contacto(contacto, respuesta, respondido_por=None):

    try:
        # Construir firma según quién responde
        firma = "El equipo de PsychCalendar"
        if respondido_por:
            if hasattr(respondido_por, 'nombre_completo'):
                firma = respondido_por.nombre_completo
            elif hasattr(respondido_por, 'nombre') and hasattr(respondido_por, 'apellido'):
                firma = f"{respondido_por.nombre} {respondido_por.apellido}"
        
        msg = Message(
            subject=f'Re: {contacto.asunto}',
            recipients=[contacto.email],
            body=f'''
            Estimado/a {contacto.nombre},
            
            En respuesta a tu mensaje:
            
            {respuesta}
            
            Saludos cordiales,
            {firma}
            ''',
            html=f'''
            <h3>Respuesta a tu consulta</h3>
            <p>Estimado/a {contacto.nombre},</p>
            <p>En respuesta a tu mensaje con asunto "{contacto.asunto}":</p>
            <div style="padding: 15px; border-left: 4px solid #4e73df; margin: 20px 0;">
                {respuesta.replace('\\n', '<br>')}
            </div>
            <p>Si tienes alguna otra consulta, no dudes en contactarnos nuevamente.</p>
            <br>
            <p>Saludos cordiales,</p>
            <p><strong>{firma}</strong></p>
            '''
        )
        mail.send(msg)
        
        # Marcar como respondido en la base de datos
        contacto.respondido = True
        db.session.commit()
        
        return True
        
    except Exception as e:
        print(f"Error al enviar respuesta de contacto: {str(e)}")
        return False


def enviar_notificacion_contacto(contacto):

    try:
        msg = Message(
            subject=f'Nuevo mensaje de contacto: {contacto.asunto}',
            recipients=['psychcalendarventas@gmail.com'],  # Lista de emails de administradores
            body=f'''
            Se ha recibido un nuevo mensaje de contacto:
            
            Nombre: {contacto.nombre}
            Email: {contacto.email}
            Teléfono: {contacto.telefono}
            Asunto: {contacto.asunto}
            
            Mensaje:
            {contacto.mensaje}
            
            Fecha: {contacto.fecha_envio.strftime('%d/%m/%Y %H:%M')}
            IP: {contacto.ip_remitente}
            ''',
            html=f'''
            <h3>Nuevo mensaje de contacto</h3>
            <p><strong>Nombre:</strong> {contacto.nombre}</p>
            <p><strong>Email:</strong> {contacto.email}</p>
            <p><strong>Teléfono:</strong> {contacto.telefono}</p>
            <p><strong>Asunto:</strong> {contacto.asunto}</p>
            <p><strong>Mensaje:</strong><br>{contacto.mensaje.replace('\\n', '<br>')}</p>
            <p><strong>Fecha:</strong> {contacto.fecha_envio.strftime('%d/%m/%Y %H:%M')}</p>
            <hr>
            <p><small>IP: {contacto.ip_remitente}</small></p>
            '''
        )
        mail.send(msg)
        
        # También puedes enviar una confirmación al remitente
        send_confirmation = True
        if send_confirmation:
            confirmation = Message(
                subject=f'Hemos recibido tu mensaje - PsychCalendar',
                recipients=[contacto.email],
                body=f'''
                Estimado/a {contacto.nombre},
                
                Hemos recibido tu mensaje con el asunto "{contacto.asunto}".
                
                Te responderemos a la brevedad posible.
                
                Saludos cordiales,
                El equipo de PsychCalendar
                ''',
                html=f'''
                <h3>Gracias por contactarnos</h3>
                <p>Estimado/a {contacto.nombre},</p>
                <p>Hemos recibido tu mensaje con el asunto "<strong>{contacto.asunto}</strong>".</p>
                <p>Te responderemos a la brevedad posible.</p>
                <br>
                <p>Saludos cordiales,</p>
                <p><strong>El equipo de PsychCalendar</strong></p>
                '''
            )
            mail.send(confirmation)
            
        return True
        
    except Exception as e:
        print(f"Error al enviar email de contacto: {str(e)}")
        # Podrías loggear el error para análisis posterior
        return False



def enviar_respuesta_contacto(contacto, respuesta, respondido_por=None):

    try:
        # Construir firma según quién responde
        firma = "El equipo de PsychCalendar"
        if respondido_por:
            if hasattr(respondido_por, 'nombre_completo'):
                firma = respondido_por.nombre_completo
            elif hasattr(respondido_por, 'nombre') and hasattr(respondido_por, 'apellido'):
                firma = f"{respondido_por.nombre} {respondido_por.apellido}"
        
        msg = Message(
            subject=f'Re: {contacto.asunto}',
            recipients=[contacto.email],
            body=f'''
            Estimado/a {contacto.nombre},
            
            En respuesta a tu mensaje:
            
            {respuesta}
            
            Saludos cordiales,
            {firma}
            ''',
            html=f'''
            <h3>Respuesta a tu consulta</h3>
            <p>Estimado/a {contacto.nombre},</p>
            <p>En respuesta a tu mensaje con asunto "{contacto.asunto}":</p>
            <div style="padding: 15px; border-left: 4px solid #4e73df; margin: 20px 0;">
                {respuesta.replace('\\n', '<br>')}
            </div>
            <p>Si tienes alguna otra consulta, no dudes en contactarnos nuevamente.</p>
            <br>
            <p>Saludos cordiales,</p>
            <p><strong>{firma}</strong></p>
            '''
        )
        mail.send(msg)
        
        # Marcar como respondido en la base de datos
        contacto.respondido = True
        db.session.commit()
        
        return True
        
    except Exception as e:
        print(f"Error al enviar respuesta de contacto: {str(e)}")
        return False