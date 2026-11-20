// Tecnotics Arcade - pantalla de bienvenida y selector de modo.
//
// Es el "escritorio" (valor Shell) de la cuenta de Windows del arcade. Al iniciar
// sesión muestra la bienvenida y, tras una cuenta atrás, abre RetroBat.
// El modo Windows está oculto: combinación secreta de botones, F12 o Ctrl+Alt+F12,
// y un PIN. Con el PIN correcto abre el escritorio normal de Windows en la misma
// cuenta. Al reiniciar se vuelve al modo arcade.
//
// Se controla con mando arcade/joystick (winmm), teclado y ratón.
//
// Parámetros:
//   /prueba   modo de prueba: no cambia de sesión, Esc cierra el programa y
//             al cerrar RetroBat el programa termina (no vuelve a empezar)
//   /botones  muestra los números de botón del mando (para configurar)
//
// Compatible con el compilador de .NET Framework 4 incluido en Windows (C# 5).

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: System.Reflection.AssemblyTitle("Tecnotics Arcade - Bienvenida")]
[assembly: System.Reflection.AssemblyProduct("Tecnotics Arcade")]
[assembly: System.Reflection.AssemblyVersion("1.2.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.2.0.0")]

namespace TecnoticsArcade
{
    static class Programa
    {
        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            bool nueva;
            using (System.Threading.Mutex unica = new System.Threading.Mutex(true, "Local\\TecnoticsArcadeBienvenida", out nueva))
            {
                if (!nueva)
                {
                    Registro.Escribir("Ya había una bienvenida abierta: no se abre otra.");
                    bool botones = false;
                    foreach (string a in args) if (a.Equals("/botones", StringComparison.OrdinalIgnoreCase)) botones = true;
                    if (!botones)
                    {
                        MessageBox.Show("La bienvenida de Tecnotics Arcade ya está funcionando.\n\n" +
                            "Para detenerla pulsa Ctrl + Alt + F12, o usa \"Detener prueba\" en el Configurador.",
                            "Tecnotics Arcade", MessageBoxButtons.OK, MessageBoxIcon.Information);
                        return;
                    }
                }
                Registro.Escribir("Inicio v" + Bienvenida.Version + " " + string.Join(" ", args));
                Application.Run(new Bienvenida(args));
                Registro.Escribir("Fin");
            }
        }
    }

    // Registro de lo que hace la bienvenida (en la carpeta temporal del usuario)
    static class Registro
    {
        public static readonly string Ruta = Path.Combine(Path.GetTempPath(), "TecnoticsArcade-registro.txt");
        public static void Escribir(string texto)
        {
            try { File.AppendAllText(Ruta, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + texto + "\r\n"); } catch { }
        }
    }

    // ------------------------------------------------------------------ config
    class Configuracion
    {
        readonly Dictionary<string, string> valores = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        public readonly string Carpeta;

        public Configuracion()
        {
            Carpeta = Path.GetDirectoryName(Application.ExecutablePath);
            string ruta = Path.Combine(Carpeta, "config.ini");
            if (!File.Exists(ruta)) return;
            foreach (string linea in File.ReadAllLines(ruta))
            {
                string l = linea.Trim();
                if (l.Length == 0 || l.StartsWith("#") || l.StartsWith(";")) continue;
                int i = l.IndexOf('=');
                if (i <= 0) continue;
                valores[l.Substring(0, i).Trim()] = l.Substring(i + 1).Trim();
            }
        }

        public string Texto(string clave, string porDefecto)
        {
            string v;
            return valores.TryGetValue(clave, out v) && v.Length > 0 ? v : porDefecto;
        }

        public int Numero(string clave, int porDefecto)
        {
            int n;
            return int.TryParse(Texto(clave, ""), out n) ? n : porDefecto;
        }

        // Lista de botones "7,8" -> máscara de bits (botón 1 = bit 0)
        public int Botones(string clave, string porDefecto)
        {
            int mascara = 0;
            foreach (string parte in Texto(clave, porDefecto).Split(new char[] { ',', '+', ' ' }, StringSplitOptions.RemoveEmptyEntries))
            {
                int b;
                if (int.TryParse(parte, out b) && b >= 1 && b <= 32) mascara |= 1 << (b - 1);
            }
            return mascara;
        }
    }

    // ------------------------------------------------------------------ mando
    class Mando
    {
        [StructLayout(LayoutKind.Sequential)]
        struct JOYINFOEX
        {
            public int dwSize, dwFlags, dwXpos, dwYpos, dwZpos, dwRpos, dwUpos, dwVpos;
            public int dwButtons, dwButtonNumber, dwPOV, dwReserved1, dwReserved2;
        }

        [DllImport("winmm.dll")]
        static extern int joyGetPosEx(int uJoyID, ref JOYINFOEX pji);

        const int JOY_RETURNALL = 0xFF;

        public int Botones;            // todos los botones pulsados (de todos los mandos)
        public bool Arriba, Abajo, Izquierda, Derecha;
        int sinMando;                  // para no consultar mandos inexistentes en cada ciclo
        readonly bool[] presente = new bool[16];
        bool desactivado;              // si la lectura falla, se sigue con teclado y ratón

        public void Leer()
        {
            Botones = 0;
            Arriba = Abajo = Izquierda = Derecha = false;
            if (desactivado) return;
            try { LeerMandos(); }
            catch (Exception) { desactivado = true; Botones = 0; }
        }

        void LeerMandos()
        {
            bool revisarTodos = (sinMando++ % 40) == 0;   // cada ~2 s se buscan mandos nuevos
            for (int id = 0; id < 16; id++)
            {
                if (!presente[id] && !revisarTodos) continue;
                JOYINFOEX j = new JOYINFOEX();
                j.dwSize = Marshal.SizeOf(typeof(JOYINFOEX));
                j.dwFlags = JOY_RETURNALL;
                presente[id] = joyGetPosEx(id, ref j) == 0;
                if (!presente[id]) continue;

                Botones |= j.dwButtons;
                if (j.dwXpos < 16384) Izquierda = true;
                if (j.dwXpos > 49151) Derecha = true;
                if (j.dwYpos < 16384) Arriba = true;
                if (j.dwYpos > 49151) Abajo = true;
                int pov = j.dwPOV;
                if (pov >= 0 && pov < 36000)
                {
                    if (pov > 27000 || pov < 9000) Arriba = true;
                    if (pov > 0 && pov < 18000) Derecha = true;
                    if (pov > 9000 && pov < 27000) Abajo = true;
                    if (pov > 18000) Izquierda = true;
                }
            }
        }
    }

    // ------------------------------------------------------------------ pantalla
    class Bienvenida : Form
    {
        [DllImport("user32.dll")] static extern bool RegisterHotKey(IntPtr hWnd, int id, int fsModifiers, int vk);
        [DllImport("user32.dll")] static extern bool UnregisterHotKey(IntPtr hWnd, int id);
        const int WM_HOTKEY = 0x0312, MOD_ALT = 0x1, MOD_CONTROL = 0x2, MOD_NOREPEAT = 0x4000, ID_EMERGENCIA = 1;

        public const string Version = "1.2.0";

        enum Estado { CuentaAtras, Pin, Arcade, EnWindows, Botones, Menu }

        // Menú que aparece al salir de RetroBat
        readonly string[] opcionesMenu = { "Volver a RetroBat", "Reiniciar el sistema", "Apagar" };
        Rectangle[] rectMenu = new Rectangle[3];
        int menuSel;
        Estado volverA = Estado.CuentaAtras;   // a dónde vuelve el PIN al cancelar

        readonly Configuracion cfg = new Configuracion();
        readonly Mando mando = new Mando();
        readonly Timer reloj = new Timer();
        readonly bool modoPrueba, modoBotones;

        Estado estado;
        DateTime inicioCuenta;
        int segundosCuenta;
        string mensaje = "";
        DateTime mensajeHasta = DateTime.MinValue;

        // combinación secreta
        int comboBotones, comboSegundos;
        Keys teclaSecreta;
        DateTime comboDesde = DateTime.MinValue;
        double pausaCuenta;            // ms de cuenta atrás congelados mientras se mantiene el combo

        // PIN
        readonly string[] teclas = { "1", "2", "3", "4", "5", "6", "7", "8", "9", "Borrar", "0", "Aceptar" };
        int seleccion = 10;
        string pin = "";
        int fallos;
        DateTime bloqueoHasta = DateTime.MinValue;
        DateTime ultimaAccion;
        Rectangle[] rectTeclas = new Rectangle[12];

        // navegación con repetición
        int botonesAntes;
        string direccionAntes = "";
        DateTime proximaRepeticion;

        // arcade
        DateTime arcadeDesde;
        int comprobacionesVacias;

        Image logo;
        bool salir;
        bool cursorOculto;
        readonly Color cFondo = Color.FromArgb(8, 11, 16);
        readonly Color cCian = Color.FromArgb(110, 198, 216);
        readonly Color cNaranja = Color.FromArgb(241, 142, 25);
        readonly Color cTexto = Color.FromArgb(232, 238, 242);
        readonly Color cSuave = Color.FromArgb(143, 163, 174);
        readonly Color cPanel = Color.FromArgb(18, 25, 33);

        public Bienvenida(string[] args)
        {
            foreach (string a in args)
            {
                if (a.Equals("/prueba", StringComparison.OrdinalIgnoreCase)) modoPrueba = true;
                if (a.Equals("/botones", StringComparison.OrdinalIgnoreCase)) modoBotones = true;
            }

            Text = "Tecnotics Arcade";
            FormBorderStyle = FormBorderStyle.None;
            WindowState = FormWindowState.Maximized;
            StartPosition = FormStartPosition.Manual;
            Bounds = Screen.PrimaryScreen.Bounds;
            BackColor = cFondo;
            DoubleBuffered = true;
            KeyPreview = true;
            ShowInTaskbar = false;
            TopMost = !modoPrueba;

            segundosCuenta = Math.Max(1, cfg.Numero("Segundos", 5));
            comboBotones = cfg.Botones("ComboBotones", "7,8");
            comboSegundos = Math.Max(1, cfg.Numero("ComboSegundos", 3));
            try { teclaSecreta = (Keys)Enum.Parse(typeof(Keys), cfg.Texto("TeclaSecreta", "F12"), true); }
            catch { teclaSecreta = Keys.F12; }

            string rutaLogo = Path.Combine(cfg.Carpeta, "logo.png");
            if (File.Exists(rutaLogo))
            {
                try { using (Image tmp = Image.FromFile(rutaLogo)) logo = new Bitmap(tmp); } catch { logo = null; }
            }

            reloj.Interval = 50;
            reloj.Tick += delegate { Ciclo(); };
            KeyDown += AlPulsarTecla;
            MouseClick += AlHacerClic;
            FormClosing += AlCerrar;
            SystemEvents.SessionSwitch += AlCambiarSesion;

            if (modoBotones) estado = Estado.Botones; else EmpezarCuenta();
            reloj.Start();
        }

        // ---------------------------------------------------------- estados
        void EmpezarCuenta()
        {
            estado = Estado.CuentaAtras;
            inicioCuenta = DateTime.Now;
            pausaCuenta = 0;
            comboDesde = DateTime.MinValue;
            if (!Visible) Show();
            Activate();
            Puntero(false);
            Invalidate();
        }

        void AbrirPin()
        {
            if (DateTime.Now < bloqueoHasta)
            {
                Mensaje("Mantenimiento bloqueado unos segundos.", 3);
                return;
            }
            volverA = estado == Estado.CuentaAtras ? Estado.CuentaAtras : Estado.Menu;
            estado = Estado.Pin;
            pin = "";
            seleccion = 10;
            ultimaAccion = DateTime.Now;
            Puntero(true);
            Invalidate();
        }

        void VolverDelPin()
        {
            if (volverA == Estado.Menu) AbrirMenu(); else EmpezarCuenta();
        }

        void AbrirMenu()
        {
            estado = Estado.Menu;
            menuSel = 0;
            comboDesde = DateTime.MinValue;
            if (!Visible) Show();
            Activate();
            Puntero(true);
            Invalidate();
        }

        void EjecutarMenu(int i)
        {
            menuSel = i;
            Registro.Escribir("Menú: " + opcionesMenu[i]);
            if (i == 0) { IniciarArcade(); return; }
            string arg = i == 1 ? "/r" : "/s";
            if (modoPrueba) { Mensaje("Modo prueba: aquí se " + (i == 1 ? "reiniciaría" : "apagaría") + " el equipo.", 4); return; }
            Mensaje(i == 1 ? "Reiniciando..." : "Apagando...", 60);
            Invalidate(); Update();
            try { Process.Start("shutdown.exe", arg + " /t 0"); }
            catch (Exception ex) { Mensaje("No se pudo: " + ex.Message, 6); }
        }

        void IniciarArcade()
        {
            string ruta = cfg.Texto("RetroBat", @"C:\RetroBat\retrobat.exe");
            if (!File.Exists(ruta))
            {
                Mensaje("No se encuentra RetroBat en " + ruta, 10);
                EmpezarCuenta();
                inicioCuenta = DateTime.Now.AddSeconds(10);
                return;
            }
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo(ruta);
                psi.WorkingDirectory = Path.GetDirectoryName(ruta);
                psi.UseShellExecute = true;
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                Mensaje("No se pudo abrir RetroBat: " + ex.Message, 10);
                EmpezarCuenta();
                return;
            }
            Registro.Escribir("RetroBat abierto: " + ruta);
            estado = Estado.Arcade;
            arcadeDesde = DateTime.Now;
            comprobacionesVacias = 0;
            Hide();
        }

        const string ClaveWinlogon = @"Software\Microsoft\Windows NT\CurrentVersion\Winlogon";

        void EntrarWindows()
        {
            if (modoPrueba)
            {
                Mensaje("PIN correcto. (Modo prueba: aquí se abriría el escritorio de Windows.)", 4);
                EmpezarCuenta();
                return;
            }
            estado = Estado.EnWindows;
            Mensaje("Abriendo el escritorio de Windows...", 60);
            Invalidate();
            Update();
            Registro.Escribir("PIN correcto: abriendo el escritorio de Windows");
            CerrarRetroBat();

            // El escritorio de esta cuenta es la bienvenida (valor Shell del usuario).
            // Para que el Explorador arranque como escritorio completo (con barra de tareas),
            // se cambia el valor a explorer.exe, se abre el Explorador y, unos segundos
            // después, se vuelve a dejar la bienvenida para el próximo arranque.
            try
            {
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(ClaveWinlogon))
                    k.SetValue("Shell", "explorer.exe");
                Process.Start(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "explorer.exe"));
            }
            catch (Exception ex)
            {
                Registro.Escribir("No se pudo abrir el Explorador: " + ex.Message);
                RestaurarEscritorioArcade();
                Mensaje("No se pudo abrir Windows: " + ex.Message, 10);
                EmpezarCuenta();
                return;
            }

            Timer espera = new Timer();
            espera.Interval = 8000;
            espera.Tick += delegate
            {
                espera.Stop();
                RestaurarEscritorioArcade();
                salir = true;
                Close();
            };
            espera.Start();
        }

        void RestaurarEscritorioArcade()
        {
            try
            {
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(ClaveWinlogon))
                    k.SetValue("Shell", Application.ExecutablePath);
                Registro.Escribir("El próximo arranque vuelve al modo arcade");
            }
            catch (Exception ex) { Registro.Escribir("No se pudo restaurar el modo arcade: " + ex.Message); }
        }

        void AlCambiarSesion(object sender, SessionSwitchEventArgs e)
        {
            // Al volver a la sesión Arcade (o desbloquearla), se reinicia la bienvenida
            if (e.Reason == SessionSwitchReason.ConsoleConnect || e.Reason == SessionSwitchReason.SessionUnlock)
            {
                BeginInvoke((MethodInvoker)delegate { if (estado == Estado.EnWindows) EmpezarCuenta(); });
            }
        }

        // ---------------------------------------------------------- ciclo
        void Ciclo()
        {
            mando.Leer();
            int nuevos = mando.Botones & ~botonesAntes;

            switch (estado)
            {
                case Estado.CuentaAtras:
                    CicloCuenta();
                    break;
                case Estado.Pin:
                    CicloPin(nuevos);
                    break;
                case Estado.Arcade:
                    CicloArcade();
                    break;
                case Estado.Menu:
                    CicloMenu(nuevos);
                    break;
            }
            botonesAntes = mando.Botones;
            if (Visible) Invalidate();
        }

        void CicloCuenta()
        {
            bool comboPulsado = comboBotones != 0 && (mando.Botones & comboBotones) == comboBotones;
            if (comboPulsado)
            {
                if (comboDesde == DateTime.MinValue) comboDesde = DateTime.Now;
                pausaCuenta += reloj.Interval;
                if ((DateTime.Now - comboDesde).TotalSeconds >= comboSegundos) { AbrirPin(); return; }
            }
            else comboDesde = DateTime.MinValue;

            if (RestanteMs() <= 0) IniciarArcade();
        }

        double RestanteMs()
        {
            return segundosCuenta * 1000.0 - ((DateTime.Now - inicioCuenta).TotalMilliseconds - pausaCuenta);
        }

        void CicloPin(int nuevos)
        {
            string dir = mando.Arriba ? "arriba" : mando.Abajo ? "abajo" : mando.Izquierda ? "izquierda" : mando.Derecha ? "derecha" : "";
            if (dir.Length > 0 && (dir != direccionAntes || DateTime.Now >= proximaRepeticion))
            {
                Mover(dir);
                proximaRepeticion = DateTime.Now.AddMilliseconds(dir != direccionAntes ? 350 : 140);
            }
            direccionAntes = dir;

            if ((nuevos & 1) != 0) Pulsar(seleccion);       // botón 1: aceptar
            else if ((nuevos & 2) != 0) VolverDelPin();      // botón 2: volver

            if ((DateTime.Now - ultimaAccion).TotalSeconds > 30) VolverDelPin();
        }

        void CicloMenu(int nuevos)
        {
            // La combinación secreta también funciona aquí
            bool comboPulsado = comboBotones != 0 && (mando.Botones & comboBotones) == comboBotones;
            if (comboPulsado)
            {
                if (comboDesde == DateTime.MinValue) comboDesde = DateTime.Now;
                if ((DateTime.Now - comboDesde).TotalSeconds >= comboSegundos) { AbrirPin(); return; }
                return;
            }
            comboDesde = DateTime.MinValue;

            string dir = mando.Arriba ? "arriba" : mando.Abajo ? "abajo" : "";
            if (dir.Length > 0 && (dir != direccionAntes || DateTime.Now >= proximaRepeticion))
            {
                menuSel = dir == "arriba" ? (menuSel + 2) % 3 : (menuSel + 1) % 3;
                proximaRepeticion = DateTime.Now.AddMilliseconds(dir != direccionAntes ? 350 : 200);
            }
            direccionAntes = dir;
            if ((nuevos & 1) != 0) EjecutarMenu(menuSel);
        }

        void CicloArcade()
        {
            // Si RetroBat se cierra, se vuelve a la bienvenida (y arranca otra vez solo)
            if ((DateTime.Now - arcadeDesde).TotalSeconds < 15) return;
            if (DateTime.Now.Millisecond > 100) return;   // comprobar ~1 vez por segundo
            bool abierto = false;
            foreach (string nombre in cfg.Texto("Procesos", "retrobat,emulationstation").Split(new char[] { ',' }))
            {
                if (Process.GetProcessesByName(nombre.Trim()).Length > 0) { abierto = true; break; }
            }
            comprobacionesVacias = abierto ? 0 : comprobacionesVacias + 1;
            if (comprobacionesVacias < 3) return;
            Registro.Escribir("RetroBat se ha cerrado: menú de Tecnotics");
            AbrirMenu();
        }

        // ---------------------------------------------------------- PIN
        void Mover(string dir)
        {
            ultimaAccion = DateTime.Now;
            int fila = seleccion / 3, col = seleccion % 3;
            if (dir == "arriba") fila = (fila + 3) % 4;
            if (dir == "abajo") fila = (fila + 1) % 4;
            if (dir == "izquierda") col = (col + 2) % 3;
            if (dir == "derecha") col = (col + 1) % 3;
            seleccion = fila * 3 + col;
        }

        void Pulsar(int indice)
        {
            ultimaAccion = DateTime.Now;
            seleccion = indice;
            string t = teclas[indice];
            if (t == "Borrar") { if (pin.Length > 0) pin = pin.Substring(0, pin.Length - 1); }
            else if (t == "Aceptar") ComprobarPin();
            else if (pin.Length < 8) pin += t;
        }

        void ComprobarPin()
        {
            string hash = cfg.Texto("PinHash", "");
            if (hash.Length == 0)
            {
                Mensaje("No hay PIN configurado. Ábrelo desde el Configurador.", 4);
                VolverDelPin();
                return;
            }
            if (string.Equals(Hash(cfg.Texto("PinSal", "") + pin), hash, StringComparison.OrdinalIgnoreCase))
            {
                fallos = 0;
                EntrarWindows();
                return;
            }
            fallos++;
            pin = "";
            if (fallos >= 3)
            {
                fallos = 0;
                bloqueoHasta = DateTime.Now.AddSeconds(60);
                VolverDelPin();
            }
            else Mensaje("Código incorrecto", 2);
        }

        static string Hash(string texto)
        {
            using (SHA256 sha = SHA256.Create())
            {
                byte[] b = sha.ComputeHash(Encoding.UTF8.GetBytes(texto));
                StringBuilder sb = new StringBuilder();
                foreach (byte x in b) sb.Append(x.ToString("x2"));
                return sb.ToString();
            }
        }

        // ---------------------------------------------------------- teclado y ratón
        void AlPulsarTecla(object sender, KeyEventArgs e)
        {
            if (modoPrueba && e.KeyCode == Keys.Escape && estado != Estado.Pin) { salir = true; Close(); return; }

            if (estado == Estado.CuentaAtras)
            {
                if (e.KeyCode == teclaSecreta) AbrirPin();
                else if (e.KeyCode == Keys.Enter) IniciarArcade();
            }
            else if (estado == Estado.Menu)
            {
                if (e.KeyCode == teclaSecreta) AbrirPin();
                else if (e.KeyCode == Keys.Up) menuSel = (menuSel + 2) % 3;
                else if (e.KeyCode == Keys.Down) menuSel = (menuSel + 1) % 3;
                else if (e.KeyCode == Keys.Enter) EjecutarMenu(menuSel);
            }
            else if (estado == Estado.Pin)
            {
                if (e.KeyCode >= Keys.D0 && e.KeyCode <= Keys.D9) Pulsar(Array.IndexOf(teclas, ((char)('0' + (e.KeyCode - Keys.D0))).ToString()));
                else if (e.KeyCode >= Keys.NumPad0 && e.KeyCode <= Keys.NumPad9) Pulsar(Array.IndexOf(teclas, ((char)('0' + (e.KeyCode - Keys.NumPad0))).ToString()));
                else if (e.KeyCode == Keys.Back) Pulsar(9);
                else if (e.KeyCode == Keys.Enter) Pulsar(11);
                else if (e.KeyCode == Keys.Escape) VolverDelPin();
                else if (e.KeyCode == Keys.Up) Mover("arriba");
                else if (e.KeyCode == Keys.Down) Mover("abajo");
                else if (e.KeyCode == Keys.Left) Mover("izquierda");
                else if (e.KeyCode == Keys.Right) Mover("derecha");
            }
            else if (estado == Estado.Botones && e.KeyCode == Keys.Escape) Close();
            e.Handled = true;
            Invalidate();
        }

        void AlHacerClic(object sender, MouseEventArgs e)
        {
            if (estado == Estado.Menu)
            {
                for (int i = 0; i < rectMenu.Length; i++)
                    if (rectMenu[i].Contains(e.Location)) { EjecutarMenu(i); break; }
                Invalidate();
                return;
            }
            if (estado != Estado.Pin) return;
            for (int i = 0; i < rectTeclas.Length; i++)
                if (rectTeclas[i].Contains(e.Location)) { Pulsar(i); break; }
            Invalidate();
        }

        void AlCerrar(object sender, FormClosingEventArgs e)
        {
            // Como escritorio del arcade, solo se cierra al apagar, cerrar sesión o entrar a Windows
            if (!modoPrueba && !modoBotones && !salir && e.CloseReason == CloseReason.UserClosing) e.Cancel = true;
        }

        void Puntero(bool visible)
        {
            if (visible && cursorOculto) { Cursor.Show(); cursorOculto = false; }
            else if (!visible && !cursorOculto) { Cursor.Hide(); cursorOculto = true; }
        }

        void Mensaje(string texto, int segundos)
        {
            mensaje = texto;
            mensajeHasta = DateTime.Now.AddSeconds(segundos);
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            // Ctrl + Alt + F12 funciona aunque RetroBat o un juego estén delante
            try
            {
                if (!RegisterHotKey(Handle, ID_EMERGENCIA, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, (int)Keys.F12))
                    Registro.Escribir("No se pudo registrar Ctrl+Alt+F12");
            }
            catch (Exception ex) { Registro.Escribir("Tecla de emergencia no disponible: " + ex.Message); }
        }

        protected override void WndProc(ref Message m)
        {
            if (m.Msg == WM_HOTKEY && m.WParam.ToInt32() == ID_EMERGENCIA) Emergencia();
            base.WndProc(ref m);
        }

        void CerrarRetroBat()
        {
            foreach (string nombre in cfg.Texto("Procesos", "retrobat,emulationstation").Split(new char[] { ',' }))
                foreach (Process p in Process.GetProcessesByName(nombre.Trim()))
                {
                    try { p.Kill(); Registro.Escribir("Cerrado " + p.ProcessName); } catch { }
                }
        }

        void Emergencia()
        {
            Registro.Escribir("Ctrl+Alt+F12 pulsado (estado " + estado + ")");
            CerrarRetroBat();
            if (modoPrueba || modoBotones) { salir = true; Close(); return; }
            // En el arcade real: se cierra RetroBat y se pide el PIN
            if (!Visible) Show();
            Activate();
            AbrirPin();
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            try { UnregisterHotKey(Handle, ID_EMERGENCIA); } catch { }
            SystemEvents.SessionSwitch -= AlCambiarSesion;
            base.OnFormClosed(e);
        }

        // ---------------------------------------------------------- dibujo
        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.AntiAliasGridFit;
            int W = ClientSize.Width, H = ClientSize.Height;
            float u = H / 1080f;   // escala respecto a 1080p

            if (estado == Estado.Botones) { DibujarBotones(g, W, H, u); return; }

            if (modoPrueba)
            {
                using (SolidBrush b = new SolidBrush(cNaranja)) g.FillRectangle(b, 0, 0, W, 44 * u);
                using (Font fp = new Font("Segoe UI", 20 * u, FontStyle.Bold, GraphicsUnit.Pixel))
                    Centrado(g, "MODO PRUEBA  ·  Ctrl + Alt + F12 o Esc para detener", fp, cFondo, W, 8 * u);
            }

            // Logo
            bool compacto = estado == Estado.Pin || estado == Estado.Menu;
            float yLogo = compacto ? 70 * u : 150 * u;
            float hLogo = compacto ? 260 * u : 420 * u;
            if (logo != null)
            {
                float wLogo = hLogo * logo.Width / logo.Height;
                g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g.DrawImage(logo, (W - wLogo) / 2, yLogo, wLogo, hLogo);
            }

            if (estado == Estado.Pin) DibujarPin(g, W, H, u);
            else if (estado == Estado.Menu) DibujarMenu(g, W, H, u);
            else DibujarCuenta(g, W, H, u, yLogo + hLogo);

            using (Font fv = new Font("Segoe UI", 16 * u, FontStyle.Regular, GraphicsUnit.Pixel))
            using (SolidBrush bv = new SolidBrush(Color.FromArgb(70, 84, 96)))
            {
                string v = "Tecnotics Arcade v" + Version;
                SizeF sz = g.MeasureString(v, fv);
                g.DrawString(v, fv, bv, W - sz.Width - 24 * u, H - sz.Height - 16 * u);
            }

            if (mensaje.Length > 0 && DateTime.Now < mensajeHasta)
            {
                using (Font f = new Font("Segoe UI", 22 * u, FontStyle.Bold, GraphicsUnit.Pixel))
                    Centrado(g, mensaje, f, cNaranja, W, H - 90 * u);
            }
        }

        void DibujarCuenta(Graphics g, int W, int H, float u, float y)
        {
            using (Font f1 = new Font("Segoe UI", 34 * u, FontStyle.Regular, GraphicsUnit.Pixel))
            using (Font f2 = new Font("Segoe UI", 64 * u, FontStyle.Bold, GraphicsUnit.Pixel))
            using (Font f3 = new Font("Segoe UI", 30 * u, FontStyle.Regular, GraphicsUnit.Pixel))
            {
                Centrado(g, "Hola, Tecnotics te da la bienvenida a", f1, cTexto, W, y + 40 * u);
                Centrado(g, "TECNOTICS ARCADE", f2, cNaranja, W, y + 95 * u);

                if (estado == Estado.CuentaAtras)
                {
                    int s = (int)Math.Ceiling(Math.Max(0, RestanteMs()) / 1000.0);
                    Centrado(g, "Iniciando Modo Arcade en " + s + "...", f3, cSuave, W, y + 210 * u);
                    float total = segundosCuenta * 1000f;
                    float p = (float)Math.Max(0, Math.Min(1, 1 - RestanteMs() / total));
                    float bw = 520 * u, bh = 8 * u, bx = (W - bw) / 2, by = y + 270 * u;
                    using (SolidBrush b = new SolidBrush(cPanel)) g.FillRectangle(b, bx, by, bw, bh);
                    using (LinearGradientBrush b = new LinearGradientBrush(new RectangleF(bx, by, bw, bh), cCian, cNaranja, 0f))
                        if (p > 0) g.FillRectangle(b, bx, by, bw * p, bh);
                }
            }
        }

        void DibujarMenu(Graphics g, int W, int H, float u)
        {
            using (Font fT = new Font("Segoe UI", 40 * u, FontStyle.Bold, GraphicsUnit.Pixel))
            using (Font fB = new Font("Segoe UI", 32 * u, FontStyle.Bold, GraphicsUnit.Pixel))
            using (Font fS = new Font("Segoe UI", 22 * u, FontStyle.Regular, GraphicsUnit.Pixel))
            {
                Centrado(g, "¿Qué quieres hacer?", fT, cTexto, W, 370 * u);
                float bw = 560 * u, bh = 96 * u, gap = 22 * u, bx = (W - bw) / 2, by = 460 * u;
                for (int i = 0; i < 3; i++)
                {
                    Rectangle r = Rectangle.Round(new RectangleF(bx, by + i * (bh + gap), bw, bh));
                    rectMenu[i] = r;
                    bool sel = i == menuSel;
                    using (GraphicsPath gp = Redondeado(r, (int)(14 * u)))
                    {
                        using (SolidBrush b = new SolidBrush(sel ? cNaranja : cPanel)) g.FillPath(b, gp);
                        using (Pen pn = new Pen(sel ? cNaranja : Color.FromArgb(40, 52, 64), 2 * u)) g.DrawPath(pn, gp);
                    }
                    SizeF sz = g.MeasureString(opcionesMenu[i], fB);
                    using (SolidBrush b = new SolidBrush(sel ? cFondo : cTexto))
                        g.DrawString(opcionesMenu[i], fB, b, r.X + (r.Width - sz.Width) / 2, r.Y + (r.Height - sz.Height) / 2);
                }
                Centrado(g, "Palanca: elegir    Botón 1: aceptar", fS, cSuave, W, by + 3 * (bh + gap) + 14 * u);
            }
        }

        void DibujarPin(Graphics g, int W, int H, float u)
        {
            using (Font fT = new Font("Segoe UI", 40 * u, FontStyle.Bold, GraphicsUnit.Pixel))
            using (Font fS = new Font("Segoe UI", 24 * u, FontStyle.Regular, GraphicsUnit.Pixel))
            using (Font fK = new Font("Segoe UI", 34 * u, FontStyle.Bold, GraphicsUnit.Pixel))
            using (Font fK2 = new Font("Segoe UI", 22 * u, FontStyle.Bold, GraphicsUnit.Pixel))
            {
                Centrado(g, "Modo mantenimiento", fT, cCian, W, 345 * u);
                Centrado(g, "Introduce el código para entrar a Windows", fS, cSuave, W, 400 * u);

                // puntos del PIN
                int n = Math.Max(4, pin.Length);
                float d = 22 * u, sep = 18 * u, x0 = (W - (n * d + (n - 1) * sep)) / 2;
                for (int i = 0; i < n; i++)
                {
                    RectangleF r = new RectangleF(x0 + i * (d + sep), 452 * u, d, d);
                    if (i < pin.Length) using (SolidBrush b = new SolidBrush(cNaranja)) g.FillEllipse(b, r);
                    else using (Pen p = new Pen(cSuave, 2 * u)) g.DrawEllipse(p, r);
                }

                // teclado numérico 3x4
                float kw = 170 * u, kh = 80 * u, gap = 16 * u;
                float kx = (W - (3 * kw + 2 * gap)) / 2, ky = 505 * u;
                for (int i = 0; i < 12; i++)
                {
                    int fila = i / 3, col = i % 3;
                    Rectangle r = Rectangle.Round(new RectangleF(kx + col * (kw + gap), ky + fila * (kh + gap), kw, kh));
                    rectTeclas[i] = r;
                    bool sel = i == seleccion;
                    using (GraphicsPath gp = Redondeado(r, (int)(12 * u)))
                    {
                        using (SolidBrush b = new SolidBrush(sel ? cNaranja : cPanel)) g.FillPath(b, gp);
                        using (Pen p = new Pen(sel ? cNaranja : Color.FromArgb(40, 52, 64), 2 * u)) g.DrawPath(p, gp);
                    }
                    string t = teclas[i];
                    Font f = t.Length > 1 ? fK2 : fK;
                    SizeF sz = g.MeasureString(t, f);
                    using (SolidBrush b = new SolidBrush(sel ? cFondo : cTexto))
                        g.DrawString(t, f, b, r.X + (r.Width - sz.Width) / 2, r.Y + (r.Height - sz.Height) / 2);
                }
                Centrado(g, "Botón 1: aceptar    Botón 2: volver", fS, cSuave, W, ky + 4 * (kh + gap) + 20 * u);
            }
        }

        void DibujarBotones(Graphics g, int W, int H, float u)
        {
            using (Font f = new Font("Segoe UI", 36 * u, FontStyle.Bold, GraphicsUnit.Pixel))
            using (Font f2 = new Font("Segoe UI", 26 * u, FontStyle.Regular, GraphicsUnit.Pixel))
            {
                Centrado(g, "Prueba de botones", f, cCian, W, 200 * u);
                Centrado(g, "Pulsa los botones del mando para ver su número. Esc para salir.", f2, cSuave, W, 270 * u);
                List<string> lista = new List<string>();
                for (int b = 0; b < 32; b++) if ((mando.Botones & (1 << b)) != 0) lista.Add((b + 1).ToString());
                string dir = (mando.Arriba ? "Arriba " : "") + (mando.Abajo ? "Abajo " : "") + (mando.Izquierda ? "Izquierda " : "") + (mando.Derecha ? "Derecha" : "");
                Centrado(g, "Botones: " + (lista.Count > 0 ? string.Join(" + ", lista.ToArray()) : "-"), f, cNaranja, W, 420 * u);
                Centrado(g, "Dirección: " + (dir.Length > 0 ? dir : "-"), f, cTexto, W, 500 * u);
                Centrado(g, "Combinación secreta configurada: " + DescribirCombo(), f2, cSuave, W, 620 * u);
            }
        }

        string DescribirCombo()
        {
            List<string> l = new List<string>();
            for (int b = 0; b < 32; b++) if ((comboBotones & (1 << b)) != 0) l.Add((b + 1).ToString());
            return l.Count > 0 ? string.Join(" + ", l.ToArray()) + " (" + comboSegundos + " s)" : "ninguna";
        }

        static void Centrado(Graphics g, string texto, Font f, Color c, int W, float y)
        {
            SizeF sz = g.MeasureString(texto, f);
            using (SolidBrush b = new SolidBrush(c)) g.DrawString(texto, f, b, (W - sz.Width) / 2, y);
        }

        static GraphicsPath Redondeado(Rectangle r, int radio)
        {
            int d = radio * 2;
            GraphicsPath gp = new GraphicsPath();
            gp.AddArc(r.X, r.Y, d, d, 180, 90);
            gp.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            gp.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            gp.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            gp.CloseFigure();
            return gp;
        }
    }
}
