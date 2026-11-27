// Tecnotics Arcade - Configurador
//
// Aplicación portable (un solo .exe) para preparar un PC como lanzador arcade
// basado en RetroBat. Lleva dentro la pantalla de bienvenida (TecnoticsArcade.exe),
// el logo y los scripts de PowerShell que hacen el trabajo.
//
// Solo usa componentes incluidos en Windows 10/11: .NET Framework 4.x y PowerShell 5.1.
// Compatible con C# 5 (compilador de .NET Framework / mcs -langversion:5).

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Reflection;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("Tecnotics Arcade - Configurador")]
[assembly: AssemblyProduct("Tecnotics Arcade")]
[assembly: AssemblyVersion("1.2.0.0")]
[assembly: AssemblyFileVersion("1.2.0.0")]

namespace TecnoticsConfigurador
{
    static class Programa
    {
        [STAThread]
        static void Main(string[] args)
        {
            // Necesita permisos de administrador: si no los tiene, se vuelve a abrir pidiéndolos
            if (!new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator))
            {
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo(Application.ExecutablePath);
                    psi.UseShellExecute = true;
                    if (args.Length == 1) psi.Arguments = "\"" + args[0] + "\"";
                    psi.Verb = "runas";
                    Process.Start(psi);
                }
                catch
                {
                    MessageBox.Show("El Configurador necesita permisos de administrador para funcionar.",
                        "Tecnotics Arcade", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
                return;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new Ventana(args.Length == 1 ? args[0] : null));
        }
    }

    class Ventana : Form
    {
        public const string Version = "1.2.0";
        const string CarpetaArcade = @"C:\TecnoticsArcade";
        readonly string temporal = Path.Combine(Path.GetTempPath(), "TecnoticsModoArcade-" + Guid.NewGuid().ToString("N"));

        readonly Color cFondo = Color.FromArgb(8, 11, 16);
        readonly Color cCian = Color.FromArgb(110, 198, 216);
        readonly Color cNaranja = Color.FromArgb(241, 142, 25);

        string retroBat;               // ruta de retrobat.exe (null si no está)
        bool ocupado;

        // controles
        Label lblRetroBat;
        Button btnBuscarRetroBat;
        TabControl pestanas;
        TextBox registro;
        Label lblTrabajando;
        ListView lvEstado;
        NumericUpDown numSegundos, numComboSeg;
        TextBox txtCombo, txtPin1, txtPin2, txtClave;
        CheckBox chkOcultar;
        Panel panelPinNuevo, panelPinExiste;
        ComboBox cmbTecla;
        ListView lvOpt;
        Label lblEdicion;
        readonly List<Control> requierenRetroBat = new List<Control>();

        public Ventana(string rutaRetroBat)
        {
            Text = "Gestor Arcade Tecnoticis · Modo arcade";
            Font = new Font("Segoe UI", 9.5f);
            Size = new Size(1000, 900);
            MinimumSize = new Size(900, 760);
            StartPosition = FormStartPosition.CenterScreen;
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }

            ExtraerRecursos();
            ConstruirInterfaz();
            DetectarRetroBat(rutaRetroBat);
            CargarConfiguracion();
            Shown += delegate { ActualizarEstado(); };
        }

        // ================================================================ recursos
        void ExtraerRecursos()
        {
            Directory.CreateDirectory(temporal);
            Assembly a = Assembly.GetExecutingAssembly();
            foreach (string nombre in a.GetManifestResourceNames())
            {
                using (Stream s = a.GetManifestResourceStream(nombre))
                using (FileStream f = File.Create(Path.Combine(temporal, nombre)))
                    s.CopyTo(f);
            }
        }

        Image Logo()
        {
            string ruta = Path.Combine(temporal, "logo.png");
            if (!File.Exists(ruta)) return null;
            using (Image tmp = Image.FromFile(ruta)) return new Bitmap(tmp);
        }

        // ================================================================ interfaz
        void ConstruirInterfaz()
        {
            // Cabecera
            Panel cabecera = new Panel { Dock = DockStyle.Top, Height = 92, BackColor = cFondo };
            PictureBox pic = new PictureBox { Image = Logo(), SizeMode = PictureBoxSizeMode.Zoom, Location = new Point(16, 10), Size = new Size(90, 72) };
            Label titulo = new Label { Text = "TECNOTICS ARCADE", ForeColor = cNaranja, Font = new Font("Segoe UI", 20f, FontStyle.Bold), AutoSize = true, Location = new Point(116, 12) };
            Label sub = new Label { Text = "Configurador del lanzador arcade (RetroBat) · v" + Version, ForeColor = cCian, Font = new Font("Segoe UI", 11f), AutoSize = true, Location = new Point(119, 52) };
            cabecera.Controls.AddRange(new Control[] { pic, titulo, sub });

            // Aviso de RetroBat
            Panel avisoRB = new Panel { Dock = DockStyle.Top, Height = 44, Padding = new Padding(12, 8, 12, 8) };
            lblRetroBat = new Label { Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft, Font = new Font("Segoe UI", 10f, FontStyle.Bold) };
            btnBuscarRetroBat = new Button { Text = "Buscar retrobat.exe…", Dock = DockStyle.Right, Width = 170 };
            btnBuscarRetroBat.Click += delegate { BuscarRetroBat(); };
            avisoRB.Controls.Add(lblRetroBat);
            avisoRB.Controls.Add(btnBuscarRetroBat);

            // Registro inferior
            Panel abajo = new Panel { Dock = DockStyle.Bottom, Height = 150, Padding = new Padding(10, 4, 10, 10) };
            lblTrabajando = new Label { Dock = DockStyle.Top, Height = 22, Text = "Registro de acciones", ForeColor = Color.DimGray };
            registro = new TextBox { Dock = DockStyle.Fill, Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Font = new Font("Consolas", 9f), BackColor = Color.FromArgb(18, 25, 33), ForeColor = Color.Gainsboro };
            abajo.Controls.Add(registro);
            abajo.Controls.Add(lblTrabajando);

            pestanas = new TabControl { Dock = DockStyle.Fill, Padding = new Point(14, 6) };
            pestanas.TabPages.Add(PestanaEstado());
            pestanas.TabPages.Add(PestanaModoArcade());
            pestanas.TabPages.Add(PestanaOptimizar());

            Controls.Add(pestanas);
            Controls.Add(abajo);
            Controls.Add(avisoRB);
            Controls.Add(cabecera);
        }

        TabPage PestanaEstado()
        {
            TabPage p = new TabPage("Estado del equipo") { Padding = new Padding(12) };
            lvEstado = new ListView { Dock = DockStyle.Fill, View = View.Details, FullRowSelect = true, HeaderStyle = ColumnHeaderStyle.Nonclickable };
            lvEstado.Columns.Add("Elemento", 260);
            lvEstado.Columns.Add("Estado", 620);
            Button act = new Button { Text = "Actualizar", Dock = DockStyle.Bottom, Height = 34 };
            act.Click += delegate { ActualizarEstado(); };
            p.Controls.Add(lvEstado);
            p.Controls.Add(act);
            return p;
        }

        TabPage PestanaModoArcade()
        {
            TabPage p = new TabPage("Modo Arcade") { Padding = new Padding(16), AutoScroll = true };
            int y = 12;
            lblEdicion = Etiqueta(p, "", 16, y, 900); lblEdicion.ForeColor = Color.DimGray; y += 30;

            Etiqueta(p, "Segundos de la cuenta atrás antes de abrir RetroBat:", 16, y + 3, 360);
            numSegundos = new NumericUpDown { Minimum = 1, Maximum = 60, Value = 5, Location = new Point(380, y), Width = 70 }; p.Controls.Add(numSegundos); y += 40;

            Etiqueta(p, "Combinación secreta del mando (números de botón):", 16, y + 3, 360);
            txtCombo = new TextBox { Text = "7,8", Location = new Point(380, y), Width = 70 }; p.Controls.Add(txtCombo);
            Etiqueta(p, "mantenida durante", 460, y + 3, 120);
            numComboSeg = new NumericUpDown { Minimum = 1, Maximum = 10, Value = 3, Location = new Point(580, y), Width = 60 }; p.Controls.Add(numComboSeg);
            Etiqueta(p, "segundos", 648, y + 3, 80); y += 40;

            Etiqueta(p, "Tecla secreta en el teclado:", 16, y + 3, 360);
            cmbTecla = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Location = new Point(380, y), Width = 70 };
            for (int i = 1; i <= 12; i++) cmbTecla.Items.Add("F" + i);
            cmbTecla.SelectedItem = "F12"; p.Controls.Add(cmbTecla); y += 50;

            Label tPin = Etiqueta(p, "PIN para entrar al modo Windows (de 4 a 8 números)", 16, y, 600);
            tPin.Font = new Font(Font, FontStyle.Bold); y += 28;

            // Sin PIN todavía: se pide dos veces
            panelPinNuevo = new Panel { Location = new Point(0, y), Size = new Size(900, 62) };
            Etiqueta(panelPinNuevo, "PIN:", 16, 3, 60);
            txtPin1 = new TextBox { UseSystemPasswordChar = true, Location = new Point(80, 0), Width = 120, MaxLength = 8 }; panelPinNuevo.Controls.Add(txtPin1);
            Etiqueta(panelPinNuevo, "Repetir:", 220, 3, 70);
            txtPin2 = new TextBox { UseSystemPasswordChar = true, Location = new Point(290, 0), Width = 120, MaxLength = 8 }; panelPinNuevo.Controls.Add(txtPin2);
            Etiqueta(panelPinNuevo, "Obligatorio: sin el PIN no se podría volver a entrar a Windows desde el arcade.", 16, 34, 700).ForeColor = Color.DimGray;
            p.Controls.Add(panelPinNuevo);

            // Ya hay PIN: solo se puede cambiar (pidiendo el actual)
            panelPinExiste = new Panel { Location = new Point(0, y), Size = new Size(900, 62) };
            Label ok = Etiqueta(panelPinExiste, "✔ PIN configurado. Se pide para entrar a Windows desde el arcade y para desactivar el Modo Arcade.", 16, 6, 700);
            ok.ForeColor = Color.DarkGreen;
            Button btnCambiar = Boton(panelPinExiste, "Cambiar PIN…", 16, 28, 170);
            btnCambiar.Click += delegate { CambiarPin(); };
            p.Controls.Add(panelPinExiste);
            y += 74;

            Label tClave = Etiqueta(p, "Contraseña de tu cuenta de Windows (" + Environment.UserName + "), para que entre sola al encender", 16, y, 900);
            tClave.Font = new Font(Font, FontStyle.Bold); y += 28;
            Etiqueta(p, "Contraseña:", 16, y + 3, 90);
            txtClave = new TextBox { UseSystemPasswordChar = true, Location = new Point(110, y), Width = 220 }; p.Controls.Add(txtClave);
            Etiqueta(p, "Déjala vacía si tu cuenta no tiene contraseña. Se comprueba antes de guardarla.", 345, y + 3, 600).ForeColor = Color.DimGray;
            y += 36;
            chkOcultar = new CheckBox { Text = "Ocultar también la pantalla \"Bienvenido\" de Windows (actívalo cuando ya hayas comprobado que el arranque funciona)", Location = new Point(16, y), Width = 900, Checked = false };
            p.Controls.Add(chkOcultar);
            y += 40;

            Button bInst = Boton(p, "Instalar / actualizar Modo Arcade", 16, y, 290); bInst.Font = new Font(Font, FontStyle.Bold);
            bInst.Click += delegate { Instalar(); }; requierenRetroBat.Add(bInst);
            Button bDes = Boton(p, "Desactivar Modo Arcade", 320, y, 220);
            bDes.Click += delegate { Desinstalar(); };
            y += 50;
            Button bPrueba = Boton(p, "Probar la bienvenida", 16, y, 200);
            bPrueba.Click += delegate { AbrirBienvenida("/prueba"); };
            Button bBotones = Boton(p, "Ver números de botones del mando", 230, y, 280);
            bBotones.Click += delegate { AbrirBienvenida("/botones"); };
            Button bDetener = Boton(p, "Detener prueba (cerrar todo)", 524, y, 250);
            bDetener.ForeColor = Color.DarkRed;
            bDetener.Click += delegate { DetenerPrueba(); };
            y += 50;
            Etiqueta(p, "Tecla de emergencia: Ctrl + Alt + F12 cierra RetroBat en cualquier momento. En la prueba cierra todo;\n" +
                        "en el arcade instalado lleva directo al PIN del modo Windows.\n\n" +
                        "Cómo entrar al modo Windows desde el arcade: durante la cuenta atrás, mantén la combinación secreta\n" +
                        "o pulsa la tecla secreta y escribe el PIN: se abre el escritorio normal de Windows. Para volver al arcade, reinicia.", 16, y, 900).ForeColor = Color.DimGray;
            return p;
        }

        // id, nombre, descripción, recomendada
        static readonly string[,] Optimizaciones = {
            { "antivirus", "Antivirus (Windows Defender)", "Excluye los discos de los análisis y apaga los análisis programados. Evita tirones y cargas lentas.", "1" },
            { "actualizaciones", "Actualizaciones de Windows", "Evita descargas, reinicios y avisos de actualización.", "1" },
            { "busqueda", "Búsqueda e indexado de archivos", "Indexa el disco en segundo plano; el arcade no lo usa.", "1" },
            { "telemetria", "Telemetría (envío de datos a Microsoft)", "Servicios que recopilan y envían datos de uso.", "1" },
            { "errores", "Informes de errores", "Evita las ventanas de \"el programa dejó de funcionar\" sobre los juegos.", "1" },
            { "notificaciones", "Notificaciones", "Ningún aviso emergente encima de los juegos.", "1" },
            { "gamebar", "Xbox Game Bar y grabación", "Overlay de Xbox que se abre con botones del mando.", "1" },
            { "energia", "Energía: alto rendimiento", "Sin suspender, sin apagar pantalla ni discos, sin hibernación.", "1" },
            { "impresion", "Impresoras y fax", "El arcade no imprime.", "1" },
            { "extras", "Mapas sin conexión y modo demo", "Servicios que nunca se usan en un arcade.", "1" },
            { "sysmain", "SysMain (Superfetch)", "Precarga programas en memoria. En discos SSD casi no aporta.", "0" },
        };

        TabPage PestanaOptimizar()
        {
            TabPage p = new TabPage("Optimizar Windows") { Padding = new Padding(12) };
            lvOpt = new ListView { Dock = DockStyle.Fill, View = View.Details, CheckBoxes = true, FullRowSelect = true, HeaderStyle = ColumnHeaderStyle.Nonclickable };
            lvOpt.Columns.Add("Opción", 270);
            lvOpt.Columns.Add("Estado", 110);
            lvOpt.Columns.Add("Para qué", 520);
            for (int i = 0; i < Optimizaciones.GetLength(0); i++)
            {
                ListViewItem it = new ListViewItem(new string[] { Optimizaciones[i, 1], "…", Optimizaciones[i, 2] });
                it.Tag = Optimizaciones[i, 0];
                it.Checked = Optimizaciones[i, 3] == "1";
                lvOpt.Items.Add(it);
            }
            FlowLayoutPanel botones = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 46, Padding = new Padding(0, 6, 0, 0) };
            Button a = new Button { Text = "Desactivar lo marcado", Width = 200, Height = 32 };
            a.Click += delegate { Optimizar("aplicar"); };
            Button r = new Button { Text = "Restaurar lo marcado", Width = 200, Height = 32 };
            r.Click += delegate { Optimizar("restaurar"); };
            Button rec = new Button { Text = "Marcar recomendadas", Width = 180, Height = 32 };
            rec.Click += delegate { for (int i = 0; i < lvOpt.Items.Count; i++) lvOpt.Items[i].Checked = Optimizaciones[i, 3] == "1"; };
            botones.Controls.AddRange(new Control[] { a, r, rec });
            p.Controls.Add(lvOpt);
            p.Controls.Add(botones);
            return p;
        }

        Label Etiqueta(Control padre, string texto, int x, int y, int ancho)
        {
            Label l = new Label { Text = texto, Location = new Point(x, y), Width = ancho, AutoSize = texto.Contains("\n") };
            if (!l.AutoSize) l.Height = 22;
            padre.Controls.Add(l);
            return l;
        }

        Button Boton(Control padre, string texto, int x, int y, int ancho)
        {
            Button b = new Button { Text = texto, Location = new Point(x, y), Width = ancho, Height = 34 };
            padre.Controls.Add(b);
            return b;
        }

        // ================================================================ RetroBat
        void DetectarRetroBat(string rutaRetroBat)
        {
            List<string> candidatos = new List<string>();
            if (!string.IsNullOrEmpty(rutaRetroBat)) candidatos.Add(rutaRetroBat);
            string ini = Path.Combine(CarpetaArcade, "config.ini");
            string deConfig = LeerIni(ini, "RetroBat");
            if (deConfig != null) candidatos.Add(deConfig);
            foreach (DriveInfo d in DriveInfo.GetDrives())
            {
                if (d.DriveType != DriveType.Fixed) continue;
                candidatos.Add(Path.Combine(d.Name, @"RetroBat\retrobat.exe"));
            }
            foreach (string rama in new string[] { @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", @"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" })
            {
                using (RegistryKey k = Registry.LocalMachine.OpenSubKey(rama))
                {
                    if (k == null) continue;
                    foreach (string sub in k.GetSubKeyNames())
                        using (RegistryKey s = k.OpenSubKey(sub))
                        {
                            string nombre = s == null ? null : s.GetValue("DisplayName") as string;
                            string lugar = s == null ? null : s.GetValue("InstallLocation") as string;
                            if (nombre != null && lugar != null && nombre.IndexOf("RetroBat", StringComparison.OrdinalIgnoreCase) >= 0)
                                candidatos.Add(Path.Combine(lugar, "retrobat.exe"));
                        }
                }
            }
            retroBat = null;
            foreach (string c in candidatos) if (File.Exists(c)) { retroBat = c; break; }
            MostrarRetroBat();
        }

        void MostrarRetroBat()
        {
            bool hay = retroBat != null;
            if (hay)
            {
                lblRetroBat.Text = "✔ RetroBat encontrado: " + retroBat;
                lblRetroBat.ForeColor = Color.DarkGreen;
                lblRetroBat.Parent.BackColor = Color.FromArgb(226, 245, 230);
            }
            else
            {
                lblRetroBat.Text = "✖ RetroBat no está instalado. Instálalo y configúralo primero; después vuelve a abrir esta herramienta.";
                lblRetroBat.ForeColor = Color.DarkRed;
                lblRetroBat.Parent.BackColor = Color.FromArgb(252, 228, 228);
            }
            foreach (Control c in requierenRetroBat) c.Enabled = hay;
        }

        void BuscarRetroBat()
        {
            using (OpenFileDialog d = new OpenFileDialog())
            {
                d.Title = "Busca retrobat.exe";
                d.Filter = "RetroBat|retrobat.exe";
                if (d.ShowDialog(this) == DialogResult.OK) { retroBat = d.FileName; MostrarRetroBat(); }
            }
        }

        // ================================================================ configuración
        static string LeerIni(string ruta, string clave)
        {
            if (!File.Exists(ruta)) return null;
            foreach (string l in File.ReadAllLines(ruta))
            {
                int i = l.IndexOf('=');
                if (i > 0 && l.Substring(0, i).Trim().Equals(clave, StringComparison.OrdinalIgnoreCase))
                {
                    string v = l.Substring(i + 1).Trim();
                    return v.Length > 0 ? v : null;
                }
            }
            return null;
        }

        void CargarConfiguracion()
        {
            string ini = Path.Combine(CarpetaArcade, "config.ini");
            decimal n;
            string v = LeerIni(ini, "Segundos"); if (v != null && decimal.TryParse(v, out n)) numSegundos.Value = Math.Max(1, Math.Min(60, n));
            v = LeerIni(ini, "ComboBotones"); if (v != null) txtCombo.Text = v;
            v = LeerIni(ini, "ComboSegundos"); if (v != null && decimal.TryParse(v, out n)) numComboSeg.Value = Math.Max(1, Math.Min(10, n));
            v = LeerIni(ini, "TeclaSecreta"); if (v != null && cmbTecla.Items.Contains(v)) cmbTecla.SelectedItem = v;
            MostrarPin();
        }

        bool HayPin()
        {
            return LeerIni(Path.Combine(CarpetaArcade, "config.ini"), "PinHash") != null;
        }

        void MostrarPin()
        {
            bool hay = HayPin();
            panelPinExiste.Visible = hay;
            panelPinNuevo.Visible = !hay;
        }

        bool PinCorrecto(string pin)
        {
            string ini = Path.Combine(CarpetaArcade, "config.ini");
            string hash = LeerIni(ini, "PinHash"), sal = LeerIni(ini, "PinSal") ?? "";
            if (hash == null || string.IsNullOrEmpty(pin)) return false;
            using (SHA256 sha = SHA256.Create())
                return string.Equals(Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(sal + pin))), hash, StringComparison.OrdinalIgnoreCase);
        }

        // Pide el PIN actual; devuelve true si es correcto
        bool PedirPinActual(string motivo)
        {
            using (DialogoPin d = new DialogoPin(motivo, true, false))
            {
                if (d.ShowDialog(this) != DialogResult.OK) return false;
                if (PinCorrecto(d.Actual)) return true;
                Avisar("PIN incorrecto. No se ha cambiado nada.");
                return false;
            }
        }

        // Devuelve "sal|hash" del PIN escrito, "" si está vacío, o null si es inválido
        string PinEscrito()
        {
            return PinValido(txtPin1.Text.Trim(), txtPin2.Text.Trim());
        }

        string PinValido(string a, string b)
        {
            if (a.Length == 0 && b.Length == 0) return "";
            if (a != b) { Avisar("Los dos PIN no coinciden."); return null; }
            if (a.Length < 4 || a.Length > 8) { Avisar("El PIN debe tener de 4 a 8 números."); return null; }
            foreach (char c in a) if (c < '0' || c > '9') { Avisar("El PIN solo puede tener números (así se puede escribir con el mando)."); return null; }
            byte[] salBytes = new byte[16];
            using (RandomNumberGenerator rng = RandomNumberGenerator.Create()) rng.GetBytes(salBytes);
            string sal = Hex(salBytes);
            using (SHA256 sha = SHA256.Create()) return sal + "|" + Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(sal + a)));
        }

        static string Hex(byte[] b)
        {
            StringBuilder sb = new StringBuilder();
            foreach (byte x in b) sb.Append(x.ToString("x2"));
            return sb.ToString();
        }

        void CambiarPin()
        {
            string ini = Path.Combine(CarpetaArcade, "config.ini");
            using (DialogoPin d = new DialogoPin("Cambiar el PIN del modo Windows", true, true))
            {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                if (!PinCorrecto(d.Actual)) { Avisar("El PIN actual no es correcto. No se ha cambiado nada."); return; }
                string pin = PinValido(d.Nuevo, d.Repetido);
                if (pin == null) return;
                if (pin.Length == 0) { Avisar("Escribe el PIN nuevo dos veces."); return; }
                string[] partes = pin.Split(new char[] { '|' });
                List<string> lineas = new List<string>();
                foreach (string l in File.ReadAllLines(ini))
                    if (!l.StartsWith("PinSal=") && !l.StartsWith("PinHash=")) lineas.Add(l);
                lineas.Add("PinSal=" + partes[0]);
                lineas.Add("PinHash=" + partes[1]);
                File.WriteAllLines(ini, lineas.ToArray());
            }
            Log("PIN del modo Windows cambiado.");
            Avisar("PIN cambiado.");
            ActualizarEstado();
        }

        // ================================================================ acciones
        void Instalar()
        {
            if (retroBat == null) { Avisar("Primero instala y configura RetroBat."); return; }
            string pin = HayPin() ? "" : PinEscrito();
            if (pin == null) return;
            if (pin.Length == 0 && !HayPin())
            {
                Avisar("Escribe el PIN del modo Windows en los dos campos.\n\n" +
                       "Es obligatorio: es la única forma de volver a entrar a Windows desde el arcade.");
                return;
            }
            string usuario = Environment.UserName;
            if (!Nativo.ClaveCorrecta(usuario, txtClave.Text))
            {
                Avisar("La contraseña de la cuenta \"" + usuario + "\" no es correcta.\n\n" +
                    "Si tu cuenta no tiene contraseña, deja el campo vacío.\nNo se ha cambiado nada.");
                return;
            }
            if (MessageBox.Show(this,
                "Se va a configurar este equipo como arcade, con tu cuenta \"" + usuario + "\":\n\n" +
                "• Al encender, Windows entra solo con tu cuenta.\n" +
                "• En lugar del escritorio aparece la bienvenida de Tecnotics, que abre RetroBat.\n" +
                "• Con el PIN se abre el escritorio normal de Windows. Al reiniciar vuelve el modo arcade.\n" +
                "• Se oculta el logo de Windows al arrancar.\n\n" +
                "Si algo fallara, mantén pulsada la tecla Shift al arrancar o usa Ctrl+Alt+F12.\n\n¿Continuar?",
                "Instalar Modo Arcade", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;

            string error = Nativo.GuardarClaveInicio(txtClave.Text);
            if (error != null) { Avisar("No se pudo guardar la contraseña cifrada: " + error + "\n\nNo se ha cambiado nada más."); return; }
            Log("Contraseña del inicio automático guardada (cifrada por Windows).");

            string sal = "", hash = "";
            if (pin.Length > 0) { string[] p = pin.Split(new char[] { '|' }); sal = p[0]; hash = p[1]; }
            string combo = txtCombo.Text.Replace(" ", "");
            Script("instalar.ps1",
                "-Origen " + Q(temporal) + " -Usuario " + Q(usuario) + " -RetroBat " + Q(retroBat) +
                " -OcultarBienvenida " + (chkOcultar.Checked ? "1" : "0") +
                " -Segundos " + numSegundos.Value + " -ComboBotones " + Q(combo) +
                " -ComboSegundos " + numComboSeg.Value + " -TeclaSecreta " + cmbTecla.SelectedItem +
                (hash.Length > 0 ? " -PinSal " + sal + " -PinHash " + hash : ""),
                delegate(int codigo)
                {
                    txtPin1.Clear(); txtPin2.Clear(); txtClave.Clear();
                    MostrarPin();
                    ActualizarEstado();
                    if (codigo == 0) Avisar("Modo Arcade instalado. Reinicia el equipo para probarlo.");
                    else if (codigo == 3) Avisar("Windows tiene que reiniciar para terminar. Reinicia, vuelve a abrir el Configurador y pulsa Instalar de nuevo.");
                    else Avisar("Hubo un error. Revisa el registro de acciones.");
                });
        }

        void Desinstalar()
        {
            if (HayPin() && !PedirPinActual("Escribe el PIN para desactivar el Modo Arcade")) return;
            if (MessageBox.Show(this, "Se desactiva el Modo Arcade y el equipo vuelve a arrancar con el escritorio normal.\n" +
                "No se borran RetroBat ni los juegos. ¿Continuar?", "Desactivar Modo Arcade",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
            Script("desinstalar.ps1", "", delegate(int c)
            {
                string e = Nativo.BorrarClaveInicio();
                Log(e == null ? "Contraseña cifrada del inicio automático borrada." : "No se pudo borrar la contraseña cifrada: " + e);
                ActualizarEstado();
            });
        }

        void Optimizar(string accion)
        {
            List<string> ids = new List<string>();
            foreach (ListViewItem it in lvOpt.Items) if (it.Checked) ids.Add((string)it.Tag);
            if (ids.Count == 0) { Avisar("Marca al menos una opción."); return; }
            Script("optimizar.ps1", "-Accion " + accion + " -Opciones " + Q(string.Join(",", ids.ToArray())),
                delegate(int c) { ActualizarEstado(); });
        }

        void DetenerPrueba()
        {
            int n = 0;
            foreach (string nombre in new string[] { "TecnoticsArcade", "retrobat", "emulationstation" })
                foreach (Process pr in Process.GetProcessesByName(nombre))
                {
                    try { pr.Kill(); n++; Log("Cerrado: " + nombre + " (" + pr.Id + ")"); }
                    catch (Exception ex) { Log("No se pudo cerrar " + nombre + ": " + ex.Message); }
                }
            Log(n == 0 ? "No había nada abierto." : "Prueba detenida.");
        }

        void AbrirBienvenida(string modo)
        {
            string instalado = Path.Combine(CarpetaArcade, "TecnoticsArcade.exe");
            string exe = File.Exists(instalado) ? instalado : Path.Combine(temporal, "TecnoticsArcade.exe");
            try { Process.Start(exe, modo); Log("Abierto " + exe + " " + modo + " (Esc para salir)"); }
            catch (Exception ex) { Avisar("No se pudo abrir: " + ex.Message); }
        }

        void ActualizarEstado()
        {
            lvEstado.Items.Clear();
            List<string> lineas = new List<string>();
            Script("estado.ps1", "", delegate(int c)
            {
                lvEstado.Items.Clear();
                lvEstado.Items.Add(new ListViewItem(new string[] { "Versión del Configurador", Version }));
                lvEstado.Items.Add(new ListViewItem(new string[] { "RetroBat", retroBat ?? "No encontrado" }));
                foreach (string l in lineas)
                {
                    int i = l.IndexOf('=');
                    if (i <= 0) continue;
                    string k = l.Substring(0, i), v = l.Substring(i + 1);
                    if (k.StartsWith("OPT:"))
                    {
                        string id = k.Substring(4);
                        foreach (ListViewItem it in lvOpt.Items)
                            if ((string)it.Tag == id)
                            {
                                it.SubItems[1].Text = v == "1" ? "Desactivado" : "Activo";
                                it.SubItems[1].ForeColor = v == "1" ? Color.DarkGreen : Color.DimGray;
                                it.UseItemStyleForSubItems = false;
                            }
                    }
                    else
                    {
                        lvEstado.Items.Add(new ListViewItem(new string[] { k, v }));
                        if (k == "Funciones de quiosco") lblEdicion.Text = v;
                    }
                }
            }, lineas, true);
        }

        // ================================================================ PowerShell
        delegate void AlTerminar(int codigo);

        void Script(string nombre, string argumentos, AlTerminar fin)
        {
            Script(nombre, argumentos, fin, null, false);
        }

        void Script(string nombre, string argumentos, AlTerminar fin, List<string> salida, bool silencioso)
        {
            if (ocupado) { Avisar("Espera a que termine la acción en curso."); return; }
            ocupado = true;
            UseWaitCursor = true;
            lblTrabajando.Text = "Trabajando… (" + nombre + ")";
            if (!silencioso) Log("\r\n>>> " + nombre);

            string ruta = Path.Combine(temporal, nombre);
            Thread t = new Thread(delegate()
            {
                int codigo = -1;
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo("powershell.exe",
                        "-NoProfile -ExecutionPolicy Bypass -File " + Q(ruta) + " " + argumentos);
                    psi.UseShellExecute = false;
                    psi.CreateNoWindow = true;
                    psi.RedirectStandardOutput = true;
                    psi.RedirectStandardError = true;
                    psi.StandardOutputEncoding = Encoding.UTF8;
                    psi.StandardErrorEncoding = Encoding.UTF8;
                    using (Process p = new Process())
                    {
                        p.StartInfo = psi;
                        p.OutputDataReceived += delegate(object s, DataReceivedEventArgs e)
                        {
                            if (e.Data == null) return;
                            if (salida != null) lock (salida) salida.Add(e.Data);
                            if (!silencioso) BeginInvoke((MethodInvoker)delegate { Log(e.Data); });
                        };
                        p.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e)
                        {
                            if (!string.IsNullOrEmpty(e.Data) && !silencioso) BeginInvoke((MethodInvoker)delegate { Log("   " + e.Data); });
                        };
                        p.Start();
                        p.BeginOutputReadLine();
                        p.BeginErrorReadLine();
                        p.WaitForExit();
                        codigo = p.ExitCode;
                    }
                }
                catch (Exception ex)
                {
                    BeginInvoke((MethodInvoker)delegate { Log("ERROR: " + ex.Message); });
                }
                BeginInvoke((MethodInvoker)delegate
                {
                    ocupado = false;
                    UseWaitCursor = false;
                    lblTrabajando.Text = "Registro de acciones";
                    if (fin != null) fin(codigo);
                });
            });
            t.IsBackground = true;
            t.Start();
        }

        static string Q(string s)
        {
            return "\"" + (s ?? "").Replace("\"", "\\\"") + "\"";
        }

        void Log(string texto)
        {
            registro.AppendText(texto + "\r\n");
            try { File.AppendAllText(Path.Combine(temporal, "registro.txt"), DateTime.Now.ToString("s") + " " + texto + "\r\n"); } catch { }
        }

        void Avisar(string texto)
        {
            MessageBox.Show(this, texto, "Tecnotics Arcade", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
    }

    // Funciones de Windows: comprobar la contraseña y guardarla cifrada para el inicio automático
    static class Nativo
    {
        [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        static extern bool LogonUser(string usuario, string dominio, string clave, int tipo, int proveedor, out IntPtr token);
        [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);

        [StructLayout(LayoutKind.Sequential)]
        struct LSA_UNICODE_STRING { public ushort Length; public ushort MaximumLength; public IntPtr Buffer; }
        [StructLayout(LayoutKind.Sequential)]
        struct LSA_OBJECT_ATTRIBUTES { public int Length; public IntPtr RootDirectory; public IntPtr ObjectName; public int Attributes; public IntPtr SecurityDescriptor; public IntPtr SecurityQualityOfService; }

        [DllImport("advapi32.dll")] static extern uint LsaOpenPolicy(IntPtr sistema, ref LSA_OBJECT_ATTRIBUTES atributos, int acceso, out IntPtr politica);
        [DllImport("advapi32.dll")] static extern uint LsaStorePrivateData(IntPtr politica, ref LSA_UNICODE_STRING clave, ref LSA_UNICODE_STRING datos);
        [DllImport("advapi32.dll", EntryPoint = "LsaStorePrivateData")] static extern uint LsaBorrarPrivateData(IntPtr politica, ref LSA_UNICODE_STRING clave, IntPtr datos);
        [DllImport("advapi32.dll")] static extern int LsaNtStatusToWinError(uint estado);
        [DllImport("advapi32.dll")] static extern uint LsaClose(IntPtr politica);

        const int POLICY_ALL_ACCESS = 0x00F0FFF;

        public static bool ClaveCorrecta(string usuario, string clave)
        {
            IntPtr token;
            // 2 = inicio de sesión interactivo, igual que el inicio automático de Windows
            if (LogonUser(usuario, ".", clave ?? "", 2, 0, out token)) { CloseHandle(token); return true; }
            // 1327: la contraseña en blanco es la correcta, pero Windows no deja usarla desde un
            // programa (directiva "limitar contraseñas en blanco"). El inicio automático sí funciona.
            int error = Marshal.GetLastWin32Error();
            return error == 1327 && string.IsNullOrEmpty(clave);
        }

        static LSA_UNICODE_STRING Cadena(string s)
        {
            LSA_UNICODE_STRING u = new LSA_UNICODE_STRING();
            u.Buffer = Marshal.StringToHGlobalUni(s);
            u.Length = (ushort)(s.Length * 2);
            u.MaximumLength = (ushort)(s.Length * 2 + 2);
            return u;
        }

        // Guarda la contraseña como secreto LSA "DefaultPassword" (lo que lee Windows para el inicio automático)
        public static string GuardarClaveInicio(string clave) { return Lsa(clave ?? ""); }
        public static string BorrarClaveInicio() { return Lsa(null); }

        static string Lsa(string clave)
        {
            LSA_OBJECT_ATTRIBUTES atr = new LSA_OBJECT_ATTRIBUTES();
            atr.Length = Marshal.SizeOf(typeof(LSA_OBJECT_ATTRIBUTES));
            IntPtr politica;
            uint r = LsaOpenPolicy(IntPtr.Zero, ref atr, POLICY_ALL_ACCESS, out politica);
            if (r != 0) return "error " + LsaNtStatusToWinError(r);
            LSA_UNICODE_STRING nombre = Cadena("DefaultPassword");
            LSA_UNICODE_STRING datos = new LSA_UNICODE_STRING();
            try
            {
                if (clave == null) r = LsaBorrarPrivateData(politica, ref nombre, IntPtr.Zero);
                else { datos = Cadena(clave); r = LsaStorePrivateData(politica, ref nombre, ref datos); }
                return r == 0 ? null : "error " + LsaNtStatusToWinError(r);
            }
            finally
            {
                Marshal.FreeHGlobal(nombre.Buffer);
                if (datos.Buffer != IntPtr.Zero) Marshal.FreeHGlobal(datos.Buffer);
                LsaClose(politica);
            }
        }
    }

    // Ventana para escribir el PIN actual y/o uno nuevo
    class DialogoPin : Form
    {
        readonly TextBox txtActual, txtNuevo, txtRepetir;
        public string Actual { get { return txtActual == null ? "" : txtActual.Text.Trim(); } }
        public string Nuevo { get { return txtNuevo == null ? "" : txtNuevo.Text.Trim(); } }
        public string Repetido { get { return txtRepetir == null ? "" : txtRepetir.Text.Trim(); } }

        public DialogoPin(string titulo, bool pedirActual, bool pedirNuevo)
        {
            Text = titulo;
            Font = new Font("Segoe UI", 10f);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false; MinimizeBox = false; ShowInTaskbar = false;
            StartPosition = FormStartPosition.CenterParent;
            int y = 18;
            if (pedirActual) txtActual = Campo("PIN actual:", ref y);
            if (pedirNuevo) { txtNuevo = Campo("PIN nuevo:", ref y); txtRepetir = Campo("Repetir PIN nuevo:", ref y); }
            Button ok = new Button { Text = "Aceptar", DialogResult = DialogResult.OK, Location = new Point(150, y + 8), Width = 100, Height = 32 };
            Button no = new Button { Text = "Cancelar", DialogResult = DialogResult.Cancel, Location = new Point(260, y + 8), Width = 100, Height = 32 };
            Controls.Add(ok); Controls.Add(no);
            AcceptButton = ok; CancelButton = no;
            ClientSize = new Size(390, y + 56);
        }

        TextBox Campo(string texto, ref int y)
        {
            Controls.Add(new Label { Text = texto, Location = new Point(16, y + 3), Width = 140 });
            TextBox t = new TextBox { UseSystemPasswordChar = true, MaxLength = 8, Location = new Point(160, y), Width = 200 };
            Controls.Add(t);
            y += 40;
            return t;
        }
    }
}
