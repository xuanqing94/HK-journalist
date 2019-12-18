import pandas as pd
import os
import matplotlib
import inspect
import matplotlib.pyplot as plt
import datetime
from tabulate import tabulate
from pathlib import Path

tex_config_path = '../config/code_block.tex'


class Journalist():
    def __init__(self, template_file=None, fig_width=None, fig_height=None, tmp_path='./temp'):
        self.template_file = template_file
        self.report_config = {'today': datetime.datetime.today().date()}
        self._width = fig_width
        self._height = fig_height
        self.var_type = {}
        self.fig_counters = 0
        self.tmp_path = tmp_path
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)
        if fig_width:
            self.fig_config = '{{ ' + f'width={fig_width}%' + ' }}'
        elif fig_height:
            self.fig_config = '{{ ' + f'height={fig_height}%' + ' }}'
        else:
            self.fig_config = ''

    def __preprocess(self, config_dict: dict):
        for k in config_dict:
            report_content = config_dict[k]
            if isinstance(report_content, pd.DataFrame):
                # transform into a string with markdown table format,
                config_dict[k] = tabulate(report_content.round(2), tablefmt='github', headers='keys')
                self.var_type[k] = 'table'

            elif isinstance(report_content, matplotlib.axes.SubplotBase):
                # save plot generated by matplotlib to a pdf format in temp directory
                fig_file = os.path.join(self.tmp_path, f'figure_{self.fig_counters}.pdf')
                self.fig_counters += 1
                ax = report_content.get_figure()
                ax.savefig(fig_file)
                config_dict[k] = fig_file
                self.var_type[k] = 'figure'

            elif callable(report_content):
                # print function definition on final report
                print(report_content)
                config_dict[k] = inspect.getsource(report_content)
                self.var_type[k] = 'function'

            elif isinstance(report_content, list) and all(isinstance(s, str) for s in report_content):
                # concatenate all words into a sentence
                config_dict[k] = str(len(report_content)) + ' ' + ', '.join(report_content)
                self.var_type[k] = 'list(str)'

            else:
                # otherwise: leave it as origin format (use its own str method)
                config_dict[k] = str(report_content).replace('\n', '\n\n')
                self.var_type[k] = 'other'

        return config_dict

    def hear(self, config_dict: dict):
        newest_config = self.__preprocess(config_dict)
        self.report_config.update(newest_config)

    def generate_template(self, template_file='./template.md'):
        if self.template_file:
            print('warning: template file was specified before and will be overwritten')
        self.template_file = template_file
        report_text = '% Report template \n% Author\n% {today}\n\n'
        for k, v in self.var_type.items():
            k_name = '{' + k + '}'
            title = f"### {k}\n\n"
            if v == 'figure':
                content = f'![]({k_name}){self.fig_config}\n\n'
            elif v == 'function':
                title = f"### {k}" + '{{.fragile}}\n\n'
                content = '```{{.python}}\n' + k_name + '\n```\n\n'
            else:
                content = k_name + '\n\n'
            report_text = report_text + title + content

        Path(template_file).write_text(report_text)
        print(f'New template file is generated in {template_file}')

    def report(self, output_file='./final_report.pdf', beamer=True, theme='default', color_theme='seagull',
               use_template_config=False, overwrite=True, aspectratio=43):
        raw_file = os.path.join(self.tmp_path, 'raw_report.md')
        report_name, ext = os.path.splitext(output_file)
        tex_command = f'--listings -H {tex_config_path}'
        if overwrite:
            final_file = output_file
        else:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            final_file = f"{report_name}_{timestamp}{ext}"

        report_template_text = open(self.template_file, 'r').read()
        Path(raw_file).write_text(report_template_text.format(**self.report_config))

        if beamer and ext == '.pdf':
            beamer_command = '-t beamer'
        else:
            beamer_command = '-t'

        if use_template_config:
            args_list = ""
        else:
            args_list = f"-V theme:{theme} -V colortheme:{color_theme} -V aspectratio:{aspectratio}"

        command = f'pandoc {beamer_command} {raw_file} {tex_command} {args_list} -s -o {final_file}'
        return_code = os.system(command)

        if return_code == 0:
            print(f'Make a big news! The newest report is now in {final_file}')
            return final_file
        else:
            print(f'Report failed with code {return_code}, please check if params and path correct')
            return return_code
