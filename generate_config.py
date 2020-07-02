from jinja2 import Environment, FileSystemLoader
import yaml
import os

def generate_config(template, data_dict):
    template_dir, template_file = os.path.split(template)

    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True)
    template = env.get_template(template_file)

    return template.render(data_dict)


if __name__ == '__main__':
    template_file = 'templates/des3526.j2'
    vars_file = 'data/fer26.yml'
    with open(vars_file) as f:
        vars_dict = yaml.safe_load(f)

    res = generate_config(template_file, vars_dict)
    with open('fer26.conf', 'w') as conf:
        conf.write(res)
