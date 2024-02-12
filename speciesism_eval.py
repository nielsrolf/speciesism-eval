import re


def extract_placeholders(text):
    return re.findall(r'\{([^\}]+)\}', text)


def get_variable_assignments(var_to_value: dict):
    try:
        key = list(var_to_value.keys())[0]
    except IndexError:
        yield {}
        return
    values =  var_to_value.pop(key)
    for assignments in get_variable_assignments(var_to_value):
        for value in values:
            yield dict(**assignments, **{key: value})


def str_to_range(value_range):
    """Turns '5-10' -> [5, ..., 10]"""
    a, b = value_range.split('-')
    a, b = int(a), int(b)
    return list(range(a, b+1))


domains = {
    'animal': ['human', 'dog', 'fish', 'chicken', 'pig', 'cow', 'horse', 'rabbit', 'turkey']
}
def get_domain(variable):
    # Hardcoded domains
    if variable in domains:
        return {variable: domains[variable]}
    # {n:5-10} or {item: a, b, c}
    if ":" in variable:
        variable, values = variable.split(":")
    else: # {5-10} or {a, b, c}
        values = variable
    if '-' in values:
        return {variable: str_to_range(values)}
    if "," in variable:
        values = [i.strip() for i in values.split(",")]
        return {variable: values}
    # e.g.: {n} when {n:5-10} will be parsed later or has already been added to the rows domain
    return {}


def get_domains(variables):
    domains = {}
    for var in variables:
        domains.update(get_domain(var))
    return domains


def row_to_tasks(row):
    # Generate all variable assignments
    tasks = {}
    variables = []
    for col in row.to_dict().keys():
        variables += extract_placeholders(row[col])
    variables = list(set(variables))
    domains = get_domains(variables)
    for assignment in get_variable_assignments(domains):
        task = row.to_dict()
        for k, v in task.items():
            if isinstance(v, str):
                task[k] = task[k].format(**assignment)
        tasks[f"{row['category']}-{assignment['animal']}-{len(tasks)}"] = task
    return tasks


def parse_judge_response(task, judge_response):
    parsed = judge_response.split("<rating>")[1].split("</rating>")[0].strip()
    parsed = parsed.split(")")[0].replace("(", "").strip()
    if parsed.endswith("%"):
        return float(parsed.replace("%", "")) / 100
    try:
        result = float(parsed)
        assert 0 <= result <= 1, f"Judge returned invalid rating: {judge_response}"
    except ValueError:
        result = parsed
        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        if result in alphabet:
            rank = alphabet.index(result)
            if rank == 0:
                return 0
        highest_rank = [alphabet.index(i) for i in alphabet if f"({i})" in task['judge_instructions']][-1]
        return rank / highest_rank
    assert False, f"Judge returned invalid rating: {judge_response}"


def get_tasks():
    import pandas as pd
    tasks_df = pd.read_csv("tasks.csv")
    tasks = {}
    for _, row in tasks_df.iterrows():
        tasks.update(row_to_tasks(row))
    return tasks


def score(task, submission: str, return_dict=False):
    import bash_agent
    judge = bash_agent.Agent(
        init_history=bash_agent.system_message_to_init_history(
            f"You are a judge evaluating a language model's response. The purpose of the test is to {task['purpose']}. Respond in a brief way and make sure to put make your answer easily parsable by following this format: <rating>b</rating> (for multiple-choice rating instructions) or <rating>xx%</rating>."
        ),
        model='gpt-4-turbo-preview',
        temperature=0
    )
    example = f"Question: {task['prompt']}\nAnswer: {submission}"
    message = f"{example}\n\n{task['judge_instructions']}\nReturn your answer enclosed in xml tags with name 'rating'."
    print(message)
    judge_response = judge.reply(message)
    print(judge_response)
    for _ in range(5):
        try:
            return parse_judge_response(task, judge_response)
        except Exception as e:
            print(type(e), e)
            judge.temperature += 0.1
    raise Exception("Judge seems confused")


if __name__ == "__main__":
    print(get_tasks())