# app.py
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException # Importar para manejo de errores específico
from flask import Flask, request, jsonify, send_from_directory
import time
import os
import math # Necesario para floor
from openpyxl.drawing.image import Image as ExcelImage 
import pandas as pd
from openpyxl import load_workbook
import matplotlib.pyplot as plt
import threading
import logging # Importar el módulo logging

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
                    handlers=[logging.StreamHandler()])

# --- Configuración de Twilio (Credenciales Directas) ---
TWILIO_ACCOUNT_SID = "ACe6fc51bff702ab5a8ddd10dd956a5313"
TWILIO_AUTH_TOKEN = "63d61de04e845e01a3ead4d8f941fcdd"
# Los números ya incluyen el prefijo 'whatsapp:' como es requerido.
TWILIO_WHATSAPP_FROM_NUMBER = "whatsapp:+14155238886" # Número de la Sandbox de Twilio
DESTINATION_WHATSAPP_NUMBER = "whatsapp:+573222074527"   # Tu número personal de WhatsApp

# --- Inicialización Global del Cliente de Twilio ---
twilio_client = None
twilio_configured_properly = False

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and \
   TWILIO_WHATSAPP_FROM_NUMBER and DESTINATION_WHATSAPP_NUMBER and \
   not TWILIO_ACCOUNT_SID.startswith("ACxxxx") and \
   not TWILIO_AUTH_TOKEN == "your_auth_token": # Chequeo básico para evitar placeholders obvios
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        twilio_configured_properly = True
        logging.info("Cliente de Twilio inicializado correctamente.")
    except Exception as e:
        logging.error(f"Fallo al inicializar el cliente de Twilio: {e}")
else:
    logging.error("Faltan credenciales de Twilio o parecen ser placeholders. Las alertas de WhatsApp no funcionarán.")


def send_whatsapp_message(message_body):
    logging.info("--- Iniciando función send_whatsapp_message ---")
    
    if not twilio_configured_properly or not twilio_client:
        logging.error("ALERTA NO ENVIADA: Cliente de Twilio no inicializado o no configurado correctamente.")
        logging.info("--- Fin send_whatsapp_message (Error de configuración de Twilio) ---")
        return False

    # Usamos las variables globales definidas arriba
    from_number_to_use = TWILIO_WHATSAPP_FROM_NUMBER
    to_number_to_use = DESTINATION_WHATSAPP_NUMBER

    logging.info(f"  Usando Account SID: {TWILIO_ACCOUNT_SID}")
    logging.info(f"  Usando Auth Token: {'Token presente (longitud: ' + str(len(TWILIO_AUTH_TOKEN)) + ')' if TWILIO_AUTH_TOKEN else '¡Token NO presente!'}")
    logging.info(f"  Usando Número Origen (From): {from_number_to_use}")
    logging.info(f"  Usando Número Destino (To): {to_number_to_use}")
    logging.info(f"  Mensaje a enviar: \"{message_body}\"")

    try:
        logging.info("  Intentando enviar mensaje via API de Twilio...")
        message_resource = twilio_client.messages.create(
            body=message_body,
            from_=from_number_to_use, 
            to=to_number_to_use       
        )
        logging.info(f"  Mensaje Twilio enviado/encolado. SID: {message_resource.sid}, Estado: {message_resource.status}")
        if message_resource.error_message:
            logging.error(f"  Error reportado por Twilio en el recurso del mensaje: {message_resource.error_message} (Código: {message_resource.error_code})")
        
        logging.info("--- Fin send_whatsapp_message (Éxito o error reportado por API) ---")
        return True

    except TwilioRestException as e:
        logging.error(f"ALERTA WHATSAPP: Error REST de Twilio al enviar mensaje: {e}")
        logging.error(f"Detalles del error de Twilio - Status: {e.status}, Code: {e.code}, URI: {e.uri}, Msg: {e.msg}")
        if hasattr(e, 'details') and e.details: logging.error(f"Twilio Error Details: {e.details}")
        logging.info("--- Fin send_whatsapp_message (Excepción TwilioRestException) ---")
        return False
    except Exception as e:
        logging.error(f"ALERTA WHATSAPP: Error general al enviar mensaje con Twilio: {type(e).__name__} - {e}")
        logging.info("--- Fin send_whatsapp_message (Excepción general en Python) ---")
        return False

# --- Inicialización de Flask ---
app = Flask(__name__, static_folder='static')

# --- Almacenamiento en Memoria ---
tasks = [
    { 'id': 'task-1', 'name': 'Diseñar Prototipo Alfa', 'estimatedTimeMinutes': 480, 'difficulty': '2', 'status': 'todo', 'startTime': None, 'endTime': None, 'efficiency': None,'wasNotifiedDelay': False},
    { 'id': 'task-2', 'name': 'Investigación de Mercado UX', 'estimatedTimeMinutes': 720, 'difficulty': '3', 'status': 'todo', 'startTime': None, 'endTime': None, 'efficiency': None,'wasNotifiedDelay': False},
    { 'id': 'task-3', 'name': 'Reunión Kick-off Proyecto K', 'estimatedTimeMinutes': 60, 'difficulty': '1', 'status': 'inprogress', 'startTime': time.time() - (30 * 60), 'endTime': None, 'efficiency': None,'wasNotifiedDelay': False},
    { 'id': 'task-4', 'name': 'Configurar Entorno Dev', 'estimatedTimeMinutes': 240, 'difficulty': '1', 'status': 'done', 'startTime': time.time() - (5 * 60 * 60), 'endTime': time.time() - (1 * 60 * 60), 'efficiency': {'text': 'Completado a tiempo (4h 0m / 4h 0m)', 'class': 'efficiency-neutral'}, 'wasNotifiedDelay': True },
]
next_task_id_counter = len(tasks) + 1

# --- Funciones Auxiliares ---
difficulty_map = { '1': 'Baja', '2': 'Media', '3': 'Alta' }
difficulty_sort_order = { '1': 1, '2': 2, '3': 3 }

def format_minutes_to_hm(total_minutes):
    if total_minutes is None or not isinstance(total_minutes, (int, float)) or total_minutes < 0:
        return "N/A"
    hours = math.floor(total_minutes / 60)
    minutes = round(total_minutes % 60)
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h 0m"
    else:
        return f"{minutes}m"

def calculate_efficiency(task):
    if task['status'] != 'done' or not task['startTime'] or not task['endTime'] or task.get('estimatedTimeMinutes') is None:
        return None
    try:
        time_taken_seconds = task['endTime'] - task['startTime']
        time_taken_minutes = time_taken_seconds / 60
        estimated_minutes = float(task['estimatedTimeMinutes'])
    except TypeError:
        return {'text': 'Error en cálculo (datos inválidos)', 'class': 'efficiency-bad'}

    difference_minutes = time_taken_minutes - estimated_minutes
    time_taken_formatted = format_minutes_to_hm(time_taken_minutes)
    estimated_formatted = format_minutes_to_hm(estimated_minutes)
    efficiency_text, efficiency_class = '', ''
    margin = estimated_minutes * 0.10

    if difference_minutes <= margin and difference_minutes >= -margin:
         efficiency_text = f"A tiempo ({time_taken_formatted} / {estimated_formatted})"
         efficiency_class = 'efficiency-neutral'
    elif difference_minutes < -margin:
        efficiency_text = f"Antes ({time_taken_formatted} / {estimated_formatted})"
        efficiency_class = 'efficiency-good'
    else:
        efficiency_text = f"Con retraso ({time_taken_formatted} / {estimated_formatted})"
        efficiency_class = 'efficiency-bad'
    return {'text': efficiency_text, 'class': efficiency_class}

# --- Rutas de la API ---
@app.route('/')
def index():
    # Servir index.html desde el directorio actual donde se ejecuta app.py
    # Asegúrate que 'index.html' esté en el mismo directorio que 'app.py'
    # o ajusta la ruta si está en una subcarpeta como 'templates' o 'static'.
    if os.path.exists('index.html'): 
         return send_from_directory('.', 'index.html')
    elif os.path.exists(os.path.join(app.static_folder, 'index.html')): # Chequeo alternativo en static_folder
         return send_from_directory(app.static_folder, 'index.html')
    else:
         logging.error("El archivo 'index.html' no se encontró en el directorio actual ni en la carpeta 'static'.")
         return "Error: El archivo principal 'index.html' no se encontró.", 404


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks_with_formatted_time = []
    for task_item in tasks:
        task_copy = task_item.copy()
        task_copy['estimatedTimeFormatted'] = format_minutes_to_hm(task_item.get('estimatedTimeMinutes'))
        tasks_with_formatted_time.append(task_copy)
    return jsonify(tasks_with_formatted_time)


@app.route('/api/tasks', methods=['POST'])
def add_task():
    global next_task_id_counter
    data = request.get_json()
    required_fields = ['name', 'estimatedTimeMinutes', 'difficulty']
    if not data or not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        logging.warning(f"Intento de añadir tarea con datos incompletos. Faltan: {', '.join(missing)}")
        return jsonify({"error": f"Datos incompletos. Faltan: {', '.join(missing)}"}), 400

    try:
        estimated_minutes = int(data['estimatedTimeMinutes'])
        if estimated_minutes <= 0: # Modificado para ser estrictamente positivo
             raise ValueError("El tiempo estimado debe ser mayor a 0 minutos.")
    except (ValueError, TypeError):
        logging.warning(f"Tiempo estimado inválido proporcionado: {data.get('estimatedTimeMinutes')}")
        return jsonify({"error": "Tiempo estimado inválido. Debe ser un número entero de minutos mayor a 0."}), 400

    new_task = {
        'id': f'task-{next_task_id_counter}', 'name': data['name'],
        'estimatedTimeMinutes': estimated_minutes, 'difficulty': data['difficulty'],
        'status': 'todo', 'startTime': None, 'endTime': None,
        'efficiency': None, 'wasNotifiedDelay': False
    }
    tasks.append(new_task)
    next_task_id_counter += 1
    logging.info(f"Tarea añadida: {new_task['name']} (ID: {new_task['id']})")

    try:
        tiempo_formateado = format_minutes_to_hm(new_task['estimatedTimeMinutes'])
        mensaje_whatsapp = (
            f"📝 *Nueva Tarea Creada*\n\n"
            f"▫️ *Nombre:* {new_task['name']}\n"
            f"🕒 *Estimado:* {tiempo_formateado}\n"
            f"📊 *Dificultad:* {difficulty_map.get(new_task['difficulty'], 'N/A')}"
        )
        send_whatsapp_message(mensaje_whatsapp)
    except Exception as e:
        logging.error(f"Excepción al intentar enviar WhatsApp para nueva tarea '{new_task['name']}': {e}")

    new_task_copy = new_task.copy()
    new_task_copy['estimatedTimeFormatted'] = format_minutes_to_hm(new_task['estimatedTimeMinutes'])
    return jsonify(new_task_copy), 201

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.get_json()
    if not data or 'status' not in data:
         logging.warning(f"Intento de actualizar tarea {task_id} sin especificar 'status'.")
         return jsonify({"error": "Falta el nuevo estado ('status') en la solicitud."}), 400

    task_to_update = None
    task_index = -1
    for i, t_iter in enumerate(tasks):
        if t_iter['id'] == task_id:
            task_to_update = t_iter
            task_index = i
            break

    if task_to_update is None:
        logging.warning(f"Intento de actualizar tarea con ID no existente: {task_id}")
        return jsonify({"error": f"Tarea con ID '{task_id}' no encontrada."}), 404

    old_status = task_to_update['status']
    new_status = data['status']

    if old_status == new_status:
        logging.info(f"Tarea {task_to_update['name']} ({task_id}) ya está en estado {new_status}. No se actualiza ni notifica.")
        task_copy = task_to_update.copy()
        task_copy['estimatedTimeFormatted'] = format_minutes_to_hm(task_to_update.get('estimatedTimeMinutes'))
        return jsonify(task_copy)

    task_to_update['status'] = new_status
    current_time = time.time()
    
    if new_status == 'inprogress':
        task_to_update['startTime'] = task_to_update.get('startTime') or current_time
        task_to_update['endTime'] = None
        task_to_update['efficiency'] = None
        task_to_update['wasNotifiedDelay'] = False
    elif new_status == 'done':
        task_to_update['startTime'] = task_to_update.get('startTime') or (current_time - 1 if old_status == 'inprogress' else None) 
        task_to_update['endTime'] = current_time
        if task_to_update['startTime']:
             task_to_update['efficiency'] = calculate_efficiency(task_to_update)
        else:
             task_to_update['efficiency'] = {'text': 'Completado (sin seguimiento de tiempo)', 'class': 'efficiency-neutral'}
    elif new_status == 'todo':
        task_to_update['startTime'], task_to_update['endTime'], task_to_update['efficiency'], task_to_update['wasNotifiedDelay'] = None, None, None, False

    if old_status != new_status:
        nombre_tarea = task_to_update.get('name', 'Desconocida')
        status_friendly_names = {'todo': 'Por Hacer 📌', 'inprogress': 'En Progreso ⚙️', 'done': 'Finalizado ✅'}
        estado_anterior_amigable = status_friendly_names.get(old_status, old_status.capitalize())
        estado_nuevo_amigable = status_friendly_names.get(new_status, new_status.capitalize())

        mensaje_whatsapp_base = (f"🔄 *Actualización de Estado de Tarea*\n\n"
                               f"▫️ *Tarea:* {nombre_tarea}\n"
                               f"⬅️ *De:* {estado_anterior_amigable}\n"
                               f"➡️ *A:* {estado_nuevo_amigable}")
        detalles_adicionales = ""
        if new_status == 'done' and task_to_update.get('efficiency'):
            detalles_adicionales = f"\n🏁 *Resultado:* {task_to_update['efficiency']['text']}"
        elif new_status == 'inprogress' and old_status == 'todo' and task_to_update.get('estimatedTimeMinutes'):
            detalles_adicionales = f"\n🕒 *Tiempo Estimado:* {format_minutes_to_hm(task_to_update['estimatedTimeMinutes'])}"
        
        mensaje_whatsapp = mensaje_whatsapp_base + detalles_adicionales
        try:
            logging.info(f"Preparando para enviar notificación de cambio de estado: {nombre_tarea} de '{old_status}' a '{new_status}'")
            send_whatsapp_message(mensaje_whatsapp)
        except Exception as e:
            logging.error(f"Excepción al intentar enviar WhatsApp para actualización de tarea '{nombre_tarea}': {e}")

    logging.info(f"Tarea actualizada: {task_to_update['name']} (ID: {task_id}) -> de '{old_status}' a '{new_status}'")
    task_copy = task_to_update.copy()
    task_copy['estimatedTimeFormatted'] = format_minutes_to_hm(task_to_update.get('estimatedTimeMinutes'))
    return jsonify(task_copy)

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    global tasks
    task_to_delete = next((t for t in tasks if t['id'] == task_id), None)
    if not task_to_delete:
        logging.warning(f"Intento de eliminar tarea con ID no existente: {task_id}")
        return jsonify({"error": f"Tarea con ID '{task_id}' no encontrada para eliminar."}), 404
    tasks = [t for t in tasks if t['id'] != task_id]
    logging.info(f"Tarea eliminada: {task_to_delete['name']} (ID: {task_id})")
    return jsonify({"message": f"Tarea '{task_to_delete['name']}' eliminada correctamente"}), 200

@app.route('/api/optimize', methods=['GET'])
def get_optimization():
    tasks_to_optimize = [t for t in tasks if t['status'] in ['todo', 'inprogress']]
    tasks_to_optimize.sort(key=lambda t: (difficulty_sort_order.get(t['difficulty'], 99), t.get('estimatedTimeMinutes', float('inf'))))
    optimized_tasks_copy = []
    for task_item in tasks_to_optimize:
        task_copy = task_item.copy()
        task_copy['estimatedTimeFormatted'] = format_minutes_to_hm(task_item.get('estimatedTimeMinutes'))
        optimized_tasks_copy.append(task_copy)
    return jsonify(optimized_tasks_copy)


@app.route('/api/progress', methods=['GET'])
def get_progress():
    total_tasks = len(tasks)
    if total_tasks == 0:
        return jsonify({'done': 0, 'pending': 0, 'total': 0, 'donePercentage': 0, 'pendingPercentage': 0})
    done_tasks = sum(1 for t in tasks if t['status'] == 'done')
    pending_tasks = total_tasks - done_tasks
    done_percentage = round((done_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
    pending_percentage = round((pending_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
    return jsonify({'done': done_tasks, 'pending': pending_tasks, 'total': total_tasks,
                    'donePercentage': done_percentage, 'pendingPercentage': pending_percentage})

@app.route('/api/export-excel', methods=['GET'])
def export_to_excel():
    if not tasks:
        logging.info("Intento de exportar a Excel sin tareas disponibles.")
        return jsonify({"error": "No hay tareas para exportar"}), 400
    df_data = []
    for task_item in tasks:
        df_data.append({
            'ID': task_item.get('id'), 
            'Nombre': task_item.get('name'),
            'Tiempo Estimado': format_minutes_to_hm(task_item.get('estimatedTimeMinutes')),
            'Dificultad': difficulty_map.get(task_item.get('difficulty'), 'N/A'),
            'Estado': task_item.get('status'),
            'Eficiencia': task_item.get('efficiency', {}).get('text', 'N/A') if task_item.get('status') == 'done' else 'N/A',
            'Inicio': time.strftime('%Y-%m-%d %H:%M', time.localtime(task_item.get('startTime'))) if task_item.get('startTime') else 'N/A',
            'Fin': time.strftime('%Y-%m-%d %H:%M', time.localtime(task_item.get('endTime'))) if task_item.get('endTime') else 'N/A'
        })
    df = pd.DataFrame(df_data)
    filename = f"reporte_tareas_kanban_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    # Considerar usar tempfile para mayor seguridad y limpieza automática en producción
    filepath = os.path.join(os.getcwd(), filename) 

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Tareas', index=False)
        worksheet = writer.sheets['Tareas']
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2 # +2 para un poco de padding
            worksheet.column_dimensions[chr(65+i)].width = column_len
        
        status_counts = df['Estado'].value_counts()
        if not status_counts.empty:
            plt.figure(figsize=(7, 5)) # Ajustar tamaño si es necesario
            plt.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', 
                    colors=[{'todo': '#f59e0b', 'inprogress': '#3b82f6', 'done': '#10b981'}.get(label, '#cccccc') for label in status_counts.index], 
                    startangle=90, wedgeprops={'edgecolor': 'white'})
            plt.title('Distribución de Tareas por Estado', fontsize=14)
            plt.axis('equal') # Asegura que el pie sea un círculo.
            plt.tight_layout()
            chart_path_status = os.path.join(os.getcwd(), 'grafico_estado_tareas.png') 
            plt.savefig(chart_path_status, bbox_inches='tight')
            plt.close() # Cerrar la figura para liberar memoria
            img_status = ExcelImage(chart_path_status)
            img_status.anchor = f'A{len(df) + 3}' # Posicionar la gráfica después de la tabla
            worksheet.add_image(img_status)
            if os.path.exists(chart_path_status):
                try:
                    os.remove(chart_path_status) # Eliminar imagen temporal
                except Exception as e_remove:
                    logging.warning(f"No se pudo eliminar el archivo temporal del gráfico: {e_remove}")
    logging.info(f"Reporte Excel '{filename}' generado exitosamente.")
    return send_file(filepath, as_attachment=True, download_name=filename)

# --- Monitor de Tareas (Ejecutado en un Hilo Separado) ---
def monitor_task_delays(interval_seconds=60 * 5): # Revisar cada 5 minutos
    logging.info(f"Monitor automático de retrasos activo (revisión cada {interval_seconds // 60} minutos)...")
    while True:
        time.sleep(interval_seconds)
        now = time.time()
        # logging.info(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Revisando tareas retrasadas...") # Descomentar para depuración verbosa
        with app.app_context(): # Necesario si el monitor interactúa con partes de Flask que requieren contexto de app
            for task_item in tasks:
                if (task_item['status'] == 'inprogress' and task_item['startTime'] and
                    not task_item.get('wasNotifiedDelay', False) and task_item.get('estimatedTimeMinutes') is not None):
                    try:
                        elapsed_minutes = (now - task_item['startTime']) / 60
                        if elapsed_minutes > task_item['estimatedTimeMinutes']:
                            msg = (f"⚠️ *Alerta de Retraso*\n\n"
                                   f"La tarea '{task_item['name']}' ha superado su tiempo estimado.\n"
                                   f"🕒 *Estimado:* {format_minutes_to_hm(task_item['estimatedTimeMinutes'])}\n"
                                   f"⏳ *Transcurrido:* {format_minutes_to_hm(elapsed_minutes)}")
                            send_whatsapp_message(msg)
                            task_item['wasNotifiedDelay'] = True # Marcar como notificada para evitar mensajes repetidos
                            logging.info(f"Notificación de retraso enviada para tarea: {task_item['name']}")
                    except Exception as e:
                        logging.error(f"Error en monitor_task_delays para tarea '{task_item.get('name', 'ID Desconocido')}': {e}")

# --- Ejecución del Servidor ---
if __name__ == '__main__':
    if not twilio_configured_properly:
        warning_message = (
            "\n" + "*"*80 +
            "\nADVERTENCIA: Credenciales/números de Twilio no configurados o son valores de ejemplo." +
            "\n             Las alertas de WhatsApp NO funcionarán." +
            "\n             Por favor, verifica las variables TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, " +
            "\n             TWILIO_WHATSAPP_FROM_NUMBER, y DESTINATION_WHATSAPP_NUMBER al inicio del script." +
            "\n" + "*"*80 + "\n"
        )
        logging.warning(warning_message)
    
    delay_monitor_thread = threading.Thread(target=monitor_task_delays, daemon=True)
    delay_monitor_thread.start()
    
    app_debug_str = os.environ.get('FLASK_DEBUG', 'True') # Default a 'True' para desarrollo
    app_debug = app_debug_str.lower() in ('true', '1', 't')
    app_port = int(os.environ.get('FLASK_PORT', 5000))
    
    logging.info(f"Servidor Flask corriendo en modo {'DEBUG' if app_debug else 'PRODUCCIÓN'}")
    logging.info(f"Accede a la aplicación en http://127.0.0.1:{app_port} o http://[TU_IP_LOCAL]:{app_port}")
    if not app_debug:
        logging.warning("El modo DEBUG de Flask está DESACTIVADO. Para producción, considera usar un servidor WSGI como Gunicorn o Waitress.")
    
    app.run(debug=app_debug, port=app_port, host='0.0.0.0')