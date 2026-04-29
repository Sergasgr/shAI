import os

def get_system_context() -> dict: 
    shell = os.environ.get('SHELL', '/bin/bash')
    lang = os.environ.get('LANG', 'en_US.UTF-8') 
    
    try:
        with open("/etc/os-release", 'r') as f:
            for line in f:
                if line.startswith("PRETTY_NAME"):
                    os_ = line.replace("PRETTY_NAME=", "").strip('"\n')
                    break       
    except FileNotFoundError:
        os_ = 'Linux/Unix'
        
    return {'os': os_, 'shell': shell, 'language': lang}          