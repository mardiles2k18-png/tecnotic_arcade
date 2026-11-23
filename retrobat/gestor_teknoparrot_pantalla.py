"""Control del ajuste HideWindow de EmulationStation en RetroBat."""
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET


def leer_ajustes(raiz):
    archivo = raiz.resolve() / "emulationstation" / ".emulationstation" / "es_settings.cfg"
    if archivo.resolve() != archivo:
        raise ValueError("El archivo de ajustes apunta a otra ubicación.")
    original = archivo.read_bytes() if archivo.exists() else None
    if original is None:
        return archivo, original, ET.Element("config")
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    try:
        config = ET.fromstring(original, parser=parser)
        if config.tag == "config":
            return archivo, original, config
    except ET.ParseError:
        pass
    # EmulationStation también admite archivos antiguos sin un elemento raíz.
    texto = original.decode("utf-16" if original.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    texto = re.sub(r"^<\?xml\s+[^?]*\?>", "", texto)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    config = ET.fromstring(f"<config>{texto}</config>", parser=parser)
    if any(isinstance(nodo.tag, str) and nodo.tag not in {"bool", "int", "float", "string"} for nodo in config):
        raise ValueError("No se reconoce el formato de es_settings.cfg.")
    return archivo, original, config


def pantalla_oculta(raiz):
    _, _, config = leer_ajustes(raiz)
    nodos = config.findall("bool[@name='HideWindow']")
    return bool(nodos) and nodos[-1].get("value", "").casefold() in {"1", "true", "yes", "on"}


def configurar_pantalla(raiz, ocultar):
    archivo, original, config = leer_ajustes(raiz)
    valor = "true" if ocultar else "false"
    nodos = config.findall("bool[@name='HideWindow']")
    if len(nodos) == 1 and nodos[0].get("value") == valor:
        return None
    for nodo in nodos:
        config.remove(nodo)
    ET.SubElement(config, "bool", name="HideWindow", value=valor)

    archivo.parent.mkdir(parents=True, exist_ok=True)
    respaldo = None
    with tempfile.TemporaryDirectory(dir=archivo.parent) as temporal:
        preparado = Path(temporal) / archivo.name
        ET.ElementTree(config).write(preparado, encoding="utf-8", xml_declaration=True)
        actual = archivo.read_bytes() if archivo.exists() else None
        if archivo.resolve() != archivo or actual != original:
            raise ValueError("RetroBat modificó sus ajustes. Ciérralo y vuelve a intentar.")
        if original is not None:
            carpeta = raiz / "user" / "tecnotics-gestor" / "respaldos-ajustes"
            carpeta.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix="es_settings-", suffix=".cfg.bak",
                                             dir=carpeta, delete=False) as copia:
                copia.write(original)
                respaldo = Path(copia.name)
        preparado.replace(archivo)
    return respaldo
