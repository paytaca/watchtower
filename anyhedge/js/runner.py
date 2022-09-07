import os
import json
from subprocess import run, PIPE

# This class gets populated with functions in the javascript after loading this file
# Refer to code below
class AnyhedgeFunctions:
    pass

def generate_func(func_name):
    def func(*args):
        _input = {
            "function": func_name,
            "params": args,
        }
        process = run(['node', './anyhedge/js/src/main.js'], input=json.dumps(_input).encode(), stdout=PIPE)
        result = None

        print(process)
        if process.stdout:
            try:
                result = json.loads(process.stdout)
            except json.JSONDecodeError:
                result = process.stdout
        elif process.stderr:
            raise Exception(process.stderr)
        return result

    return func

process = run(['node', '/code/anyhedge/js/src/load.js'], stdout=PIPE)
functions = []
print (process)
if process.stdout:
    functions = json.loads(process.stdout)

for function in functions:
    setattr(AnyhedgeFunctions, function, staticmethod(generate_func(function)))