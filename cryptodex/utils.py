def ask(question, console=None):
    prompt = f"{question}? (Y/N): "
    if console:
        answer = console.input(prompt).strip()
    else:
        answer = input(prompt).strip()
    if answer.lower() not in ["y", "n"]:
        return ask(question, console)
    return answer.lower() == "y"
