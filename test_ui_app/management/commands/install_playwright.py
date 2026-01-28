"""
安装Playwright浏览器的管理命令
"""
from django.core.management.base import BaseCommand
import subprocess
import sys


class Command(BaseCommand):
    help = '安装Playwright浏览器'

    def add_arguments(self, parser):
        parser.add_argument(
            '--browser',
            type=str,
            choices=['chromium', 'firefox', 'webkit', 'all'],
            default='all',
            help='要安装的浏览器类型'
        )

    def handle(self, *args, **options):
        browser = options['browser']
        
        self.stdout.write(self.style.SUCCESS(f'开始安装Playwright浏览器: {browser}'))
        
        try:
            if browser == 'all':
                subprocess.check_call([sys.executable, '-m', 'playwright', 'install'])
            else:
                subprocess.check_call([sys.executable, '-m', 'playwright', 'install', browser])
            
            self.stdout.write(self.style.SUCCESS('Playwright浏览器安装成功！'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'安装失败: {e}'))
            sys.exit(1)

