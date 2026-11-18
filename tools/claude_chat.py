"""Chat with Claude through the API, preloaded with this repo's STATUS.md, findings and playbook.
Run from anywhere: python3 tools/claude_chat.py   (needs: pip install anthropic, and ANTHROPIC_API_KEY or `ant auth login`)
No broker access: paste positions or quotes in yourself. Type quit to stop."""
import pathlib
import anthropic

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = ["STATUS.md", "docs/findings.md", ".claude/skills/fable-playbook/SKILL.md"]

context = "\n\n".join(
    f"=== {name} ===\n{(ROOT / name).read_text()}"
    for name in FILES
    if (ROOT / name).exists()
)

system = (
    "You are the research assistant for this options-trading-lab project. "
    "Follow the playbook below. You have no broker access: never claim to see live "
    "positions or quotes; ask the user to paste them. Never invent numbers.\n\n"
    + context
)

client = anthropic.Anthropic()
history = []

while True:
    user = input("\nYou: ").strip()
    if user.lower() in {"quit", "exit"}:
        break
    if not user:
        continue
    history.append({"role": "user", "content": user})
    reply = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=2000,
        system=system,
        messages=history,
    )
    text = "".join(b.text for b in reply.content if b.type == "text")
    history.append({"role": "assistant", "content": text})
    print(f"\nClaude: {text}")
