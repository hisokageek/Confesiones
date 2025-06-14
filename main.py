import sys
# Asegurar que usamos python-telegram-bot y no el paquete telegram conflictivo
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
except ImportError as e:
    print(f"Error de importación: {e}")
    print("Asegúrate de que python-telegram-bot esté instalado correctamente")
    sys.exit(1)

from keep_alive import keep_alive

# =========================
# CONFIGURA ESTO
# =========================
BOT_TOKEN = '7904080480:AAFbValrlMywBoCfHQMXk8cWthREWIx-onU'
CANAL_ID = -1002839547708
ADMINES = [1539799148]  # Tu ID de Telegram aqui (y los de otros admin si quieres anadirlos desde ya)

# =========================
# VARIABLES EN MEMORIA
# =========================
pendientes = {}  # id_unico: {"texto":..., "user_id":...}
esperando_motivo = {}  # {admin_id: {"conf_id": ..., "user_id": ...}}

# =========================
# COMANDOS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bienvendido a ConfesionesUCLV, publique su confesión y en breve será revisada por algún administrador, "
        "es totalmente anónimo, podrá ver los comentarios en cuanto sea publicada"
    )

async def obtener_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para obtener el ID del chat actual"""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = getattr(update.effective_chat, 'title', 'Sin título')
    
    await update.message.reply_text(
        f"📊 Información del chat:\n"
        f"ID: {chat_id}\n"
        f"Tipo: {chat_type}\n"
        f"Título: {chat_title}"
    )
    print(f"Chat ID: {chat_id}, Tipo: {chat_type}, Título: {chat_title}")

async def agregar_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINES:
        await update.message.reply_text("No tienes permiso para hacer eso.")
        return
    try:
        nuevo_id = int(context.args[0])
        if nuevo_id not in ADMINES:
            ADMINES.append(nuevo_id)
            await update.message.reply_text(f"Admin añadido: {nuevo_id}")
        else:
            await update.message.reply_text("Ese usuario ya es admin.")
    except:
        await update.message.reply_text("Uso correcto: /agregaradmin <id_usuario>")

async def admin_confesion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINES:
        await update.message.reply_text("No tienes permiso para usar este comando.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso correcto: /adminconf <tu confesión>")
        return
    
    texto = " ".join(context.args)
    conf_id = str(update.message.message_id)
    pendientes[conf_id] = {"texto": texto, "user_id": update.effective_user.id}

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Aceptar", callback_data=f"aceptar:{conf_id}"),
         InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar:{conf_id}")]
    ])
    for admin in ADMINES:
        await context.bot.send_message(
            chat_id=admin,
            text=f"📝 Nueva confesión de ADMIN:\n\n{texto}",
            reply_markup=keyboard
        )
    await update.message.reply_text("Tu confesión de admin fue enviada para revisión.")

# =========================
# MANEJO DE CONFESIONES
# =========================

# Variable global para controlar los motivos de rechazo
esperando_motivo = {}  # {admin_id: {"conf_id": ..., "user_id": ...}}

async def recibir_confesion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Validar que el mensaje y el texto existan
    if not update.message or not update.message.text:
        return
    
    # Verificar si es un admin escribiendo motivo de rechazo
    if update.effective_user.id in ADMINES and update.effective_user.id in esperando_motivo:
        motivo = update.message.text
        datos_rechazo = esperando_motivo[update.effective_user.id]

        conf_id = datos_rechazo["conf_id"]
        user_id = datos_rechazo["user_id"]
        
        # Enviar motivo al usuario que envió la confesión
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Tu confesión fue rechazada.\n\n📋 Motivo: {motivo}"
            )
            await update.message.reply_text("✅ Motivo de rechazo enviado al usuario.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error al enviar motivo: {e}")
        
        # Limpiar estados
        esperando_motivo.pop(update.effective_user.id)
        if conf_id in pendientes:
            pendientes.pop(conf_id)
        return
    
    # Verificar si el usuario es admin (los admins no pueden confesar por mensaje normal)
    if update.effective_user.id in ADMINES:
        await update.message.reply_text(
            "ℹ️ Los administradores no pueden enviar confesiones por mensaje normal.\n"
            "Si quieres confesar, usa: /adminconf <tu confesión>"
        )
        return
    
    texto = update.message.text
    
    # Verificar longitud mínima de 60 caracteres
    if len(texto) < 60:
        await update.message.reply_text(
            f"❌ Tu confesión debe tener al menos 60 caracteres.\n"
            f"Actualmente tiene {len(texto)} caracteres. Añade {60 - len(texto)} más."
        )
        return
    
    conf_id = str(update.message.message_id)
    pendientes[conf_id] = {"texto": texto, "user_id": update.effective_user.id}

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Aceptar", callback_data=f"aceptar:{conf_id}"),
         InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar:{conf_id}")]
    ])
    for admin in ADMINES:
        await context.bot.send_message(
            chat_id=admin,
            text=f"📝 Nueva confesión recibida ({len(texto)} caracteres):\n\n{texto}",
            reply_markup=keyboard
        )
    await update.message.reply_text("Tu confesión fue enviada para revisión. Gracias.")

async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accion, conf_id = query.data.split(":")

    if query.from_user.id not in ADMINES:
        await query.edit_message_text("No estás autorizado para tomar esta acción.")
        return

    if conf_id not in pendientes:
        await query.edit_message_text("Esta confesión ya fue procesada.")
        return

    texto = pendientes[conf_id]["texto"]

    if accion == "aceptar":
        try:
            mensaje_confesion = f"Nueva confesión:\n\n{texto}\n\n📝 Para hacer una confesión pincha aquí @ConfesionesUCLVBot"
            await context.bot.send_message(chat_id=CANAL_ID, text=mensaje_confesion)
            await query.edit_message_text("✅ Confesión publicada.")
            print(f"Confesión publicada exitosamente en {CANAL_ID}")
        except Exception as e:
            print(f"Error al publicar confesión: {e}")
            await query.edit_message_text("❌ Error al publicar confesión. Verifica que el bot esté en el canal.")
            return
    elif accion == "rechazar":
        # Marcar que este admin está esperando escribir un motivo
        esperando_motivo[query.from_user.id] = {
            "conf_id": conf_id,
            "user_id": pendientes[conf_id]["user_id"]
        }
        
        await query.edit_message_text(
            "❌ Confesión marcada para rechazo.\n\n"
            "📝 Escribe tu siguiente mensaje con el motivo del rechazo:"
        )
        return

    pendientes.pop(conf_id)

# =========================
# CONFIGURACIÓN DEL BOT
# =========================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(CommandHandler("agregaradmin", agregar_admin))
app.add_handler(CommandHandler("adminconf", admin_confesion))
app.add_handler(CommandHandler("chatid", obtener_chat_id))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_confesion))
app.add_handler(CallbackQueryHandler(manejar_callback))

# Iniciar el servidor keep_alive
keep_alive()

print("🚀 Bot iniciado y servidor keep_alive activo en puerto 5000")
app.run_polling()