"""Templates for localized offline phrasing of gate suggestions."""

from __future__ import annotations

__all__ = ["PhraseTemplates", "get_template"]

from functools import lru_cache
from typing import Final, NamedTuple

from app.models.enums import Language, UrgencyTier


class PhraseTemplates(NamedTuple):
    """Named tuple containing phrasing template strings for different urgency tiers."""

    normal: str
    hurry: str
    critical: str


# Mapping of languages to their respective template strings
TEMPLATES: Final[dict[Language, PhraseTemplates]] = {
    Language.EN: PhraseTemplates(
        normal=(
            "Head to {gate_name} (congestion: {congestion_level}). It is the best route "
            "to Section {section}. Total distance is {distance:.0f}m, taking about "
            "{time:.0f} minutes. Landmarks: {landmarks_str}."
        ),
        hurry=(
            "Urgent: Kickoff is approaching! Direct route to Section {section} is via "
            "{gate_name} (congestion: {congestion_level}). Walking distance is "
            "{distance:.0f}m (takes about {time:.0f} minutes)."
        ),
        critical=(
            "CRITICAL: Kickoff is imminent! Head immediately to {gate_name} for entry "
            "to Section {section}. Walking time: {time:.0f} minutes. Landmarks: {landmarks_str}."
        ),
    ),
    Language.ES: PhraseTemplates(
        normal=(
            "Diríjase a {gate_name} (congestión: {congestion_level}). Es la mejor ruta "
            "para la Sección {section}. La distancia total es de {distance:.0f}m, "
            "aproximadamente {time:.0f} minutos. Puntos de referencia: {landmarks_str}."
        ),
        hurry=(
            "¡Urgente: Se acerca el saque inicial! La ruta directa a la Sección {section} "
            "es por {gate_name} (congestión: {congestion_level}). Distancia a pie: "
            "{distance:.0f}m (toma {time:.0f} minutos)."
        ),
        critical=(
            "CRÍTICO: ¡El saque de centro es inminente! Diríjase de inmediato a "
            "{gate_name} para ingresar a la Sección {section}. Tiempo de caminata: "
            "{time:.0f} minutos. Puntos de referencia: {landmarks_str}."
        ),
    ),
    Language.FR: PhraseTemplates(
        normal=(
            "Dirigez-vous vers {gate_name} (encombrement: {congestion_level}). C'est le "
            "meilleur itinéraire vers la Section {section}. Distance totale: {distance:.0f}m, "
            "environ {time:.0f} minutes. Repères: {landmarks_str}."
        ),
        hurry=(
            "Urgent: Le coup d'envoi approche! L'itinéraire direct vers la Section {section} "
            "passe par {gate_name} (encombrement: {congestion_level}). Distance de marche: "
            "{distance:.0f}m (environ {time:.0f} minutes)."
        ),
        critical=(
            "CRITIQUE: Le coup d'envoi est imminent! Allez immédiatement à {gate_name} "
            "pour accéder à la Section {section}. Temps de marche: {time:.0f} minutes. "
            "Repères: {landmarks_str}."
        ),
    ),
    Language.HI: PhraseTemplates(
        normal=(
            "{gate_name} की ओर जाएं (भीड़ का स्तर: {congestion_level})। सेक्शन {section} "
            "तक पहुँचने का यह सबसे अच्छा मार्ग है। कुल दूरी {distance:.0f} मीटर है, जिसमें लगभग "
            "{time:.0f} मिनट लगेंगे। मार्ग बिंदु: {landmarks_str}।"
        ),
        hurry=(
            "त्वरित: किकऑफ का समय निकट है! सेक्शन {section} का सीधा मार्ग {gate_name} "
            "(भीड़ का स्तर: {congestion_level}) से है। दूरी {distance:.0f} मीटर है "
            "(लगभग {time:.0f} मिनट लगेंगे)।"
        ),
        critical=(
            "गंभीर: किकऑफ शुरू होने वाला है! सेक्शन {section} में तुरंत प्रवेश के लिए अभी "
            "{gate_name} की ओर बढ़ें। चलने में {time:.0f} मिनट लगेंगे। मार्ग बिंदु: {landmarks_str}।"
        ),
    ),
}


@lru_cache(maxsize=16)
def get_template(language: Language, urgency: UrgencyTier) -> str:
    """Retrieves and caches the localized template string for a language and urgency.

    Time Complexity: O(1)
    Space Complexity: O(1)

    Args:
        language: The preferred Language enum.
        urgency: The calculated UrgencyTier enum.

    Returns:
        The matching template string.

    """
    phrase_templates = TEMPLATES.get(language, TEMPLATES[Language.EN])
    if urgency == UrgencyTier.CRITICAL:
        return phrase_templates.critical
    if urgency == UrgencyTier.HURRY:
        return phrase_templates.hurry
    return phrase_templates.normal
