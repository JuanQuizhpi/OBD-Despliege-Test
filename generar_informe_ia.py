import os
import google.generativeai as genai

# Configurar API Key desde variable de entorno
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise Exception("❌ No se encontró GEMINI_API_KEY en las variables de entorno.")

genai.configure(api_key=api_key)

def generar_informe_ia(codigo, vehiculo):
    prompt = f"""
Eres un asistente técnico automotriz especializado en interpretar códigos OBD-II (DTC).

Código detectado: {codigo}

Información del vehículo:
Marca: {vehiculo.get("marca")}
Modelo: {vehiculo.get("modelo")}
Año: {vehiculo.get("anio")}
Número de chasis: {vehiculo.get("vin")}

Debes responder en el siguiente formato (mantener encabezados):

# 🔧 Título descriptivo

## Código detectado  
Explicación corta y en lenguaje sencillo.

## ¿Qué significa este código?  
Explicación clara sin tecnicismos innecesarios.

## ¿Qué puede ocurrir si sigo conduciendo?  
Consecuencias posibles.

## Tipo de código  
Indicar si es genérico o específico del fabricante.

## Recomendación personalizada  
Acciones sugeridas según el modelo del vehículo.

## Repuesto sugerido (solo si aplica)  
- Nombre del repuesto  
- Compatibilidad aproximada  
- Rango estimado de precios  
- (Opcional) Enlace de referencia

## Nota adicional  
Información útil: frecuencia del problema, emisiones, consejos preventivos.

Estilo: profesional, amigable, claro. No asustes al usuario innecesariamente.
"""

    model = genai.GenerativeModel("gemini-2.5-flash")

    response = model.generate_content(prompt)

    return response.text
