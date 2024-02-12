import re
import click
import pandas as pd

from speciesism_eval import get_tasks, score
from agents import agents


def print_help_and_exit(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    print("Available tasks:\n  " + "\n  ".join(get_tasks().keys()))
    print("\nAvailable agents:\n  " + "\n  ".join(agents.keys()))
    ctx.exit()


def run_all(task_regex, agent_regex, csv):
    try:
        done = pd.read_csv(csv)
    except FileNotFoundError:
        done = None
        
    data = []
    
    tasks = get_tasks()
    task_ids = list(tasks.keys())
    agent_ids = list(agents.keys())
    
    for task_id in task_ids:
        if not re.match(task_regex, task_id):
            continue
        for agent_id in agent_ids:
            if not re.match(agent_regex, agent_id):
                continue
            if done is not None and len(done.loc[(done.agent_id==agent_id) & (done.task_id==task_id)]) > 0:
                print(f"Found agent={agent_id} on task={task_id} in previous run - skipping")
                continue
            print(f"Running {task_id} on {agent_id}")
            agent = agents[agent_id]['class'](**agents[agent_id]['kwargs'])
            task = tasks[task_id]
            try:
                submission = agent.reply(task['prompt'])
                result = score(task, submission)
                data.append(dict(**task, score=result, submission=submission, agent_id=agent_id, task_id=task_id))
                if csv:
                    df = pd.DataFrame(data)
                    if done is not None:
                        df = pd.concat([done, df], ignore_index=True)
                    df.to_csv(csv)
            except Exception as e:
                import traceback
                traceback.print_exc()
                return data


@click.command()
@click.argument('task', type=str)
@click.argument('agent', type=str)
@click.option('--csv', type=click.Path(), help='Path to save the CSV output.')
@click.option('--help', is_flag=True, callback=print_help_and_exit,
              expose_value=False, is_eager=True, help="Show this message and exit.")
def main(task: str, agent: str, csv: str):
    task_regex = re.escape(task).replace("\\*", ".*")
    agent_regex = re.escape(agent).replace("\\*", ".*")
    run_all(task_regex, agent_regex, csv)
    
    


if __name__ == "__main__":
    main()
