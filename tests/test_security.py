import pytest
from shai.ai.engine import check_forbidden, is_critical

def test_forbidden_commands():
    assert check_forbidden("rm -rf /") == True
    assert check_forbidden("mkfs.ext4 /dev/sda1") == True
    assert check_forbidden("sudo chmod 777 /etc") == True
    assert check_forbidden("wipefs -a /dev/nvme0n1") == True
    assert check_forbidden("ls -la") == False
    assert check_forbidden("cat /var/log/syslog") == False
    assert check_forbidden("grep 'error' file.txt") == False

def test_critical_paths():
    assert is_critical("/etc/nginx/nginx.conf") == True
    assert is_critical("/boot/grub/grub.cfg") == True
    assert is_critical("~/.ssh/id_rsa") == True

test_matrix = [
    {"path": "/etc/nginx/nginx.conf", "blocked": True},
    {"path": "/boot/grub/grub.cfg", "blocked": True},
    {"path": "~/.ssh/authorized_keys", "blocked": True},
    {"path": "~/.bashrc", "blocked": True},
    {"path": "../../../../../etc/shadow", "blocked": True},
    {"path": "/home/user/../../../etc/passwd", "blocked": True},
    {"path": "./generated_script.sh", "blocked": False},
    {"path": "/tmp/test_output.txt", "blocked": False},
    {"path": "my_folder/fake_etc_backup.txt", "blocked": False},
    {"path": "~/projects/shai/README.md", "blocked": False}
]

@pytest.mark.parametrize("case", test_matrix)
def test_path_traversal_prevention(case):
    result = is_critical(case["path"])
    assert result == case["blocked"], f"Vulnerability detected: The path '{case['path']}' was not evaluated correctly."