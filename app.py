import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
import threading
import time
from mqtt_client import MqttClient
from datetime import datetime
import re
import random
import string
from encryption import Fernet, base64, PBKDF2HMAC, hashes, default_backend

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔒 WalkieTalkie (MQTT)")
        self.root.geometry("900x700")
        self.root.configure(bg='#2c2c2c') # Fondo general más oscuro
        self.root.resizable(True, True)
        
        # Variables
        self.username = ""
        self.client = None
        self.connected = False
        self.message_count = 0
        self.current_encryption_key = ""
        
        # Configurar fuentes personalizadas
        self.setup_fonts()
        
        # Configurar estilo
        self.setup_styles()
        
        # Crear interfaz
        self.create_login_interface()
        
    def setup_fonts(self):
        """Configurar fuentes personalizadas"""
        self.title_font = font.Font(family="Arial", size=24, weight="bold") # Más grande para LOGIN
        self.subtitle_font = font.Font(family="Arial", size=12, weight="normal") # Normal para etiquetas
        self.normal_font = font.Font(family="Arial", size=12, weight="normal") # Normal para entradas y texto
        self.small_font = font.Font(family="Arial", size=10, weight="normal") # Más pequeño para info
        
    def setup_styles(self):
        """Configurar estilos personalizados"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores del tema basados en la imagen
        self.colors = {
            'background': '#2c2c2c', # Fondo principal
            'surface': '#3c3c3c',    # Fondo de los campos de entrada y botones
            'text_light': '#ffffff', # Texto claro
            'text_dark': '#e0e0e0',  # Texto en campos de entrada
            'button_bg': '#4a4a4a',  # Fondo de los botones
            'button_active': '#5a5a5a', # Fondo de los botones al pasar el ratón
            'accent': '#007bff',     # Color de acento (no muy visible en la imagen, pero útil)
            'status_disconnected': '#e74c3c', # Rojo para desconectado
            'status_connecting': '#f39c12',   # Naranja para conectando
            'status_connected': '#27ae60',    # Verde para conectado
        }
        
        # Configurar estilos personalizados
        style.configure('TLabel', 
                       background=self.colors['background'], 
                       foreground=self.colors['text_light'], 
                       font=self.normal_font)
        
        style.configure('Title.TLabel', 
                       background=self.colors['background'], 
                       foreground=self.colors['text_light'], 
                       font=self.title_font)
        
        style.configure('TButton',
                       background=self.colors['button_bg'],
                       foreground=self.colors['text_light'],
                       font=self.normal_font,
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat',
                       padding=10) # Aumentar padding para botones más grandes
        
        style.map('TButton',
                 background=[('active', self.colors['button_active']),
                           ('pressed', self.colors['button_bg'])])
        
        # Estilo para los campos de entrada (Entry)
        style.configure('TEntry',
                       fieldbackground=self.colors['surface'],
                       foreground=self.colors['text_dark'],
                       borderwidth=0,
                       relief='flat',
                       padding=5)
        
        style.map('TEntry',
                 fieldbackground=[('focus', self.colors['surface'])])

    def create_gradient_frame(self, parent, color1, color2, height=None):
        """Crear un frame con efecto degradado simulado (simplificado a un solo color)"""
        frame = tk.Frame(parent, bg=color1, height=height)
        if height:
            frame.pack_propagate(False)
        return frame
    
    def create_login_interface(self):
        """Crear la interfaz de login mejorada"""
        # Limpiar ventana
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Frame principal (ahora un solo color de fondo)
        main_frame = tk.Frame(self.root, bg=self.colors['background'])
        main_frame.pack(expand=True, fill='both')
        
        # Título principal "LOGIN"
        title_label = tk.Label(main_frame, text="LOGIN", 
                             bg=self.colors['background'], 
                             fg=self.colors['text_light'], 
                             font=self.title_font)
        title_label.pack(pady=(80, 40))
        
        # Contenedor para los campos de entrada
        input_container = tk.Frame(main_frame, bg=self.colors['background'])
        input_container.pack(padx=100, pady=20)
        
        # Campo de nombre de usuario
        name_label = tk.Label(input_container, text="Username", 
                             bg=self.colors['background'], 
                             fg=self.colors['text_light'], 
                             font=self.normal_font)
        name_label.pack(anchor='w', pady=(0, 5))
        
        self.name_entry = tk.Entry(input_container, font=self.normal_font, 
                                  bg=self.colors['surface'], 
                                  fg=self.colors['text_dark'], 
                                  insertbackground=self.colors['text_light'], # Color del cursor
                                  relief='flat', bd=0)
        self.name_entry.pack(fill='x', pady=(0, 20), ipady=5) # ipady para altura interna
        self.name_entry.bind('<Return>', lambda e: self.connect_to_chat())
        
        # Campo de MQTT Topic
        topic_label = tk.Label(input_container, text="MQTT Topic (e.g. chat/general)", 
                              bg=self.colors['background'], 
                              fg=self.colors['text_light'], 
                              font=self.normal_font)
        topic_label.pack(anchor='w', pady=(0, 5))
        
        topic_frame = tk.Frame(input_container, bg=self.colors['background'])
        topic_frame.pack(fill='x', pady=(0, 20))
        
        self.topic_entry = tk.Entry(topic_frame, font=self.normal_font, 
                                   bg=self.colors['surface'], 
                                   fg=self.colors['text_dark'], 
                                   insertbackground=self.colors['text_light'],
                                   relief='flat', bd=0)
        self.topic_entry.pack(side='left', expand=True, fill='x', ipady=5)
        
        generate_topic_btn = ttk.Button(topic_frame, text="Generate", 
                                        command=self.generate_random_topic)
        generate_topic_btn.pack(side='right', padx=(10, 0))
        
        # Campo de Encryption Key
        key_label = tk.Label(input_container, text="Encryption Key (32 chars)", 
                            bg=self.colors['background'], 
                            fg=self.colors['text_light'], 
                            font=self.normal_font)
        key_label.pack(anchor='w', pady=(0, 5))
        
        key_frame = tk.Frame(input_container, bg=self.colors['background'])
        key_frame.pack(fill='x', pady=(0, 5))
        
        self.key_entry = tk.Entry(key_frame, font=self.normal_font, 
                                 bg=self.colors['surface'], 
                                 fg=self.colors['text_dark'], 
                                 insertbackground=self.colors['text_light'],
                                 relief='flat', bd=0)
        self.key_entry.pack(side='left', expand=True, fill='x', ipady=5)
        
        generate_key_btn = ttk.Button(key_frame, text="Generate", 
                                      command=self.generate_random_key)
        generate_key_btn.pack(side='right', padx=(10, 0))
        
        self.generated_key_display = tk.Label(input_container, text="", 
                                             bg=self.colors['background'], 
                                             fg=self.colors['text_light'], 
                                             font=self.small_font, wraplength=300)
        self.generated_key_display.pack(pady=(0, 30))
        
        # Botón de conectar
        connect_btn = ttk.Button(main_frame, text="Connect to Chat", 
                                command=self.connect_to_chat)
        connect_btn.pack(pady=(0, 20), ipadx=20, ipady=10) # ipadx/ipady para tamaño del botón
        
        # Estado de conexión
        self.status_label = tk.Label(main_frame, text="Disconnected", 
                                   bg=self.colors['background'], 
                                   fg=self.colors['status_disconnected'], 
                                   font=self.normal_font)
        self.status_label.pack(pady=(0, 20))
        
        # Enfocar el campo de entrada
        self.name_entry.focus()

    def generate_random_topic(self):
        random_topic_parts = []
        for _ in range(3):
            part_length = random.randint(5, 10)
            random_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=part_length))
            random_topic_parts.append(random_part)
        random_topic = "chat/" + ".".join(random_topic_parts)
        self.topic_entry.delete(0, tk.END)
        self.topic_entry.insert(0, random_topic)

    def generate_random_key(self):
        key = Fernet.generate_key().decode()
        self.key_entry.delete(0, tk.END)
        self.key_entry.insert(0, key)
        self.generated_key_display.config(text=f"Generated Key: {key}")
        self.current_encryption_key = key
    
    # Los métodos on_entry_focus_in y on_entry_focus_out ya no son necesarios con el nuevo estilo
    # Se pueden eliminar o dejar vacíos si no se usan.
    def on_entry_focus_in(self, event):
        pass
    
    def on_entry_focus_out(self, event):
        pass
    
    def connect_to_chat(self):
        """Conectar al chat MQTT"""
        username = self.name_entry.get().strip()
        mqtt_topic = self.topic_entry.get().strip()
        encryption_key_str = self.key_entry.get().strip()

        if not username:
            messagebox.showerror("Error", "Please enter a valid username")
            return
        
        if len(username) < 2:
            messagebox.showerror("Error", "Username must be at least 2 characters long")
            return
        
        if not re.match("^[a-zA-Z0-9_áéíóúñÁÉÍÓÚÑ ]+$", username):
            messagebox.showerror("Error", "Username can only contain letters, numbers, and spaces")
            return

        if not mqtt_topic:
            self.generate_random_topic()
            mqtt_topic = self.topic_entry.get().strip()
            messagebox.showinfo("Info", f"No MQTT topic specified. A random one was generated: {mqtt_topic}")

        if not encryption_key_str:
            self.generate_random_key()
            encryption_key_str = self.key_entry.get().strip()
            messagebox.showinfo("Info", "No encryption key specified. A random one was generated.")
        
        # Validar la clave de cifrado (debe ser una clave Fernet válida)
        try:
            # Intentar crear un objeto Fernet para validar la clave
            Fernet(encryption_key_str.encode())
        except Exception as e:
            messagebox.showerror("Error", f"Invalid encryption key: {e}. It must be a valid Fernet key (32 bytes base64url-encoded).")
            return

        self.username = username
        self.current_encryption_key = encryption_key_str
        self.update_status("Connecting...", self.colors['status_connecting'])
        
        # Crear cliente MQTT
        client_id = f"secure_chat_user_{int(time.time() * 1000)}"
        # Pasar el tópico y la clave al cliente MQTT
        self.client = MqttClient(client_id=client_id, topic=mqtt_topic, encryption_key=encryption_key_str)
        self.client.set_message_callback(self.display_message)
        
        # Intentar conectar en un hilo separado
        threading.Thread(target=self._connect_thread, daemon=True).start()
    
    def update_status(self, text, color):
        #Actualizar estado de conexión
        self.status_label.config(text=text, fg=color)
    
    def _connect_thread(self):
        #Hilo para conectar al broker MQTT
        try:
            success = self.client.connect_test()
            if success:
                time.sleep(2)  # Dar tiempo para la conexión
                self.connected = True
                self.root.after(0, self.create_chat_interface)
                # Enviar mensaje de entrada
                self.client.publish_message(f"🟢 {self.username} joined the chat")
            else:
                self.root.after(0, lambda: self.update_status("Connection Error", self.colors['status_disconnected']))
                messagebox.showerror("Error", "Could not connect to MQTT broker")
        except Exception as e:
            self.root.after(0, lambda: self.update_status("Connection Error", self.colors['status_disconnected']))
            messagebox.showerror("Error", f"Connection error: {str(e)}")
    
    def create_chat_interface(self):
        """Crear la interfaz principal del chat mejorada"""
        # Limpiar ventana
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.colors['background'])
        main_frame.pack(expand=True, fill='both')
        
        # Header con degradado (simplificado a un solo color)
        header_frame = tk.Frame(main_frame, bg=self.colors['surface'])
        header_frame.pack(fill='x', ipady=10)
        
        # Contenido del header
        header_content = tk.Frame(header_frame, bg=self.colors['surface'])
        header_content.pack(expand=True, fill='both', padx=20, pady=5)
        
        # Lado izquierdo del header
        left_header = tk.Frame(header_content, bg=self.colors['surface'])
        left_header.pack(side='left', fill='y')
        
        # Icono y título
        title_container = tk.Frame(left_header, bg=self.colors['surface'])
        title_container.pack(side='left')
        
        icon_title = tk.Label(title_container, text="🔒", font=("Arial", 20), 
                             bg=self.colors['surface'], fg=self.colors['text_light'])
        icon_title.pack(side='left', padx=(0, 10))
        
        chat_title = tk.Label(title_container, text=f"WalkieTalkie - {self.username}", 
                             bg=self.colors['surface'], fg=self.colors['text_light'], 
                             font=self.subtitle_font)
        chat_title.pack(side='left')
        
        # Lado derecho del header
        right_header = tk.Frame(header_content, bg=self.colors['surface'])
        right_header.pack(side='right', fill='y')
        
        # Contador de mensajes
        self.message_counter = tk.Label(right_header, text="📊 0 messages", 
                                       bg=self.colors['surface'], fg=self.colors['text_light'], 
                                       font=self.small_font)
        self.message_counter.pack(side='right', padx=(0, 20))
        
        # Estado de conexión
        self.connection_status = tk.Label(right_header, text="🟢 Connected", 
                                        bg=self.colors['surface'], fg=self.colors['status_connected'], 
                                        font=self.normal_font)
        self.connection_status.pack(side='right', padx=(0, 20))
        
        # Botón desconectar
        disconnect_btn = ttk.Button(right_header, text="🚪 Exit", 
                                   command=self.disconnect_chat)
        disconnect_btn.pack(side='right')
        
        # Área de mensajes con marco
        messages_container = tk.Frame(main_frame, bg=self.colors['background'])
        messages_container.pack(expand=True, fill='both', padx=20, pady=(10, 0))
        
        # Marco para el área de mensajes
        messages_frame = tk.Frame(messages_container, bg=self.colors['surface'], relief='flat', bd=0)
        messages_frame.pack(expand=True, fill='both')
        
        # ScrolledText para mensajes con estilo personalizado
        self.messages_text = scrolledtext.ScrolledText(
            messages_frame, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            bg=self.colors['surface'], # Fondo del área de texto
            fg=self.colors['text_light'],
            font=self.normal_font,
            relief='flat',
            borderwidth=0,
            selectbackground=self.colors['accent'],
            selectforeground='white'
        )
        self.messages_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Configurar tags para diferentes tipos de mensajes
        self.messages_text.tag_configure("system", foreground="#7f8c8d", font=self.small_font)
        self.messages_text.tag_configure("own", foreground=self.colors['accent'], font=self.subtitle_font)
        self.messages_text.tag_configure("other", foreground="#CE7730", font=self.subtitle_font)
        self.messages_text.tag_configure("timestamp", foreground="#95a5a6", font=self.small_font)
        self.messages_text.tag_configure("join", foreground="#27ae60", font=self.normal_font)
        self.messages_text.tag_configure("leave", foreground="#e74c3c", font=self.normal_font)
        
        # Frame de entrada con estilo
        input_container = tk.Frame(main_frame, bg=self.colors['background'])
        input_container.pack(fill='x', padx=20, pady=(10, 20))
        
        input_frame = tk.Frame(input_container, bg=self.colors['surface'], relief='flat', bd=0)
        input_frame.pack(fill='x')
        
        # Contenido del frame de entrada
        input_content = tk.Frame(input_frame, bg=self.colors['surface'])
        input_content.pack(fill='x', padx=10, pady=10)
        
        # Campo de entrada de mensaje con placeholder
        self.message_entry = tk.Entry(input_content, font=self.normal_font, 
                                     bg=self.colors['surface'], 
                                     fg=self.colors['text_light'], 
                                     insertbackground=self.colors['text_light'],
                                     relief='flat', bd=0)
        self.message_entry.pack(side='left', expand=True, fill='x', ipady=5, padx=(0, 10))
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        
        # Placeholder
        self.add_placeholder()
        
        # Botón enviar con icono
        send_btn = ttk.Button(input_content, text="Send", 
                             command=self.send_message)
        send_btn.pack(side='right')
        
        # Enfocar el campo de entrada
        self.message_entry.focus()
        
        # Mensaje de bienvenida
        self.add_system_message("Welcome to WalkieTalkie! 🔐 All messages are encrypted and secured! :)")
        self.add_system_message("Type your message and press Enter or click Send!")
    
    def add_placeholder(self):
        """Agregar placeholder al campo de mensaje"""
        self.placeholder_text = ""
        self.message_entry.insert(0, self.placeholder_text)
        self.message_entry.config(fg='#95a5a6')
    
    def on_message_entry_focus_in(self, event):
        """Manejar enfoque en el campo de mensaje"""
        if self.message_entry.get() == self.placeholder_text:
            self.message_entry.delete(0, tk.END)
            self.message_entry.config(fg=self.colors['text_light'])
    
    def on_message_entry_focus_out(self, event):
        """Manejar pérdida de enfoque en el campo de mensaje"""
        if not self.message_entry.get():
            self.add_placeholder()
    
    def add_system_message(self, message):
        """Agregar mensaje del sistema"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.messages_text.insert(tk.END, f"🤖 SYSTEM: {message}\n", "system")
        self.messages_text.config(state=tk.DISABLED)
        self.messages_text.see(tk.END)
    
    def display_message(self, message):
        """Mostrar mensaje recibido con formato mejorado"""
        def update_gui():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.messages_text.config(state=tk.NORMAL)
            self.messages_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            
            # Determinar tipo de mensaje y aplicar formato
            if "joined the chat" in message.lower():
                self.messages_text.insert(tk.END, f"{message}\n", "join")
            elif "left the chat" in message.lower():
                self.messages_text.insert(tk.END, f"{message}\n", "leave")
            elif message.startswith(f"🟢 {self.username}") or message.startswith(f"({self.username}):"):
                self.messages_text.insert(tk.END, f"👤 {message}\n", "own")
            else:
                self.messages_text.insert(tk.END, f"💬 {message}\n", "other")
            
            self.messages_text.config(state=tk.DISABLED)
            self.messages_text.see(tk.END)
            
            # Actualizar contador
            self.message_count += 1
            self.message_counter.config(text=f"📊 {self.message_count} messages")
        
        # Ejecutar en el hilo principal de la GUI
        self.root.after(0, update_gui)
    
    def send_message(self):
        """Enviar mensaje con validación mejorada"""
        message = self.message_entry.get().strip()
        if not message or message == self.placeholder_text:
            return
        
        if not self.connected or not self.client:
            messagebox.showerror("Error", "You are not connected to the chat")
            return
        
        if len(message) > 500:
            messagebox.showerror("Error", "Message is too long (max 500 characters)")
            return
        
        try:
            # Enviar mensaje
            full_message = f"({self.username}): {message}"
            self.client.publish_message(full_message)
            
            # Limpiar campo de entrada y restaurar placeholder
            self.message_entry.delete(0, tk.END)
            self.add_placeholder()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error sending message: {str(e)}")
    
    def disconnect_chat(self):
        """Desconectar del chat con confirmación"""
        if messagebox.askyesno("Confirm", "Are you sure you want to exit the chat?"):
            # Ejecutar la desconexión en un hilo separado para no bloquear la GUI
            threading.Thread(target=self._disconnect_thread, daemon=True).start()

    def _disconnect_thread(self):
        """Hilo para desconectar del broker MQTT"""
        if self.connected and self.client:
            try:
                # Enviar mensaje de salida
                self.client.publish_message(f"🔴 {self.username} left the chat")
                time.sleep(0.5)  # Dar tiempo para enviar el mensaje
                
                # Desconectar
                self.client.disconnect()
                self.connected = False
                
            except Exception as e:
                print(f"Error disconnecting: {e}")
            finally:
                # Volver a la interfaz de login en el hilo principal de la GUI
                self.root.after(0, self.create_login_interface)
    
    def on_closing(self):
        """Manejar cierre de ventana"""
        if self.connected and self.client:
            try:
                self.client.publish_message(f"🔴 {self.username} left the chat")
                self.client.disconnect()
            except:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ChatGUI(root)
    
    # Configurar icono de ventana
    try:
        # PyInstaller crea una carpeta temporal _MEI donde se extraen los archivos --add-data
        # Necesitamos encontrar la ruta a esa carpeta para acceder al icono.
        import sys
        import os
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, 'resources', 'icon.ico')
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Error al establecer el icono de la ventana: {e}")
    
    # Manejar cierre de ventana
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Centrar ventana
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Configurar tamaño mínimo
    root.minsize(600, 500)
    
    root.mainloop()

if __name__ == "__main__":
    main()