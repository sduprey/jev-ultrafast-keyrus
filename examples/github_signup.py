"""Remplit le formulaire d'inscription GitHub avec jev-ultrafast, sans OpenRouter.

    uv run --env-file .env python examples/github_signup.py signup.json

TypeSafe choisit toujours l'action (clic, saisie, sélection). Les valeurs tapées
viennent de signup.json au lieu d'un LLM : aucun TEXT_MODEL_API_KEY n'est nécessaire.
"""

import json
import sys
import time

import jev_ultrafast.agent as agent_module
from jev_ultrafast import Agent

data = json.loads(open(sys.argv[1] if len(sys.argv) > 1 else "signup.json", encoding="utf-8").read())

# Mots-clés cherchés dans le libellé du champ -> valeur à taper. L'ordre compte.
FIELDS = [
    (("username", "nom d'utilisateur"), data["username"]),
    (("email", "e-mail", "courriel"), data["email"]),
    (("country", "region", "pays", "filter", "filtre"), data["country"]),
]


def local_field_text(context):
    """Remplace l'appel au LLM : renvoie la valeur du JSON correspondant au libellé du champ."""
    label = (context["field"].get("label") or "").lower()
    for keywords, value in FIELDS:
        if any(k in label for k in keywords):
            return value, {"model": "signup.json", "latency_ms": 0, "usage": {}}
    raise ValueError(f"Aucune valeur dans signup.json pour le champ « {label} » ; rien n'a été tapé.")


agent_module.field_text = local_field_text

opt_in = "coche" if data.get("email_preferences") else "décoche"
GOAL = (
    "Fill in the GitHub sign-up form. "
    f"Email: {data['email']}. Username: {data['username']}. Country/Region: {data['country']}. "
    "The password field is already filled; do not touch it. "
    f"Email preferences checkbox (receive product updates): {'checked' if data.get('email_preferences') else 'unchecked'}. "
    "Then click the Create account button. Stop when the verification puzzle or the next step appears."
)

agent = Agent(data["url"], GOAL)
browser = agent.browser

# Les champs mot de passe sont volontairement invisibles pour l'agent (snapshot.js les ignore).
# On le remplit donc directement, avant que l'agent ne commence. Il n'est jamais envoyé à TypeSafe.
found = browser.evaluate(
    "(() => { const e = document.querySelector('#password, input[type=password]');"
    " if (!e) return false; e.focus(); return true; })()"
)
if not found:
    agent.close()
    raise SystemExit("Champ mot de passe introuvable sur la page.")
browser.call("Input.insertText", text=data["password"])
time.sleep(0.2)
agent.state["page"] = browser.observe(screenshot=False)

print(f"Mot de passe rempli. Préférence email : {opt_in}. L'agent démarre…")
for state in agent.run():
    last = state["history"][-1] if state["history"] else {}
    print(f"{state['elapsed_ms']:>6} ms  {state['status']:<9} {last.get('action', '')}  {last.get('text') or ''}")

print("\nTerminé :", state["status"], "-", state["page"]["url"])
print("L'onglet reste ouvert dans Chrome : résolvez la vérification et entrez le code reçu par email.")
# agent.close() n'est pas appelé exprès, pour garder l'onglet ouvert.
