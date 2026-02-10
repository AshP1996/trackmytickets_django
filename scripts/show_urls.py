import os
import sys
import django
from django.urls import get_resolver

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def list_urls(lis, acc=None):
    if acc is None:
        acc = []
    if not lis:
        return
    l = lis[0]
    if isinstance(l, list):
        pass
    else:
        # Check if it has url_patterns (Include)
        if hasattr(l, 'url_patterns'):
            list_urls(l.url_patterns, acc + [str(l.pattern)])
        else:
            print(''.join(acc) + str(l.pattern))
    if len(lis) > 1:
        list_urls(lis[1:], acc)

def show_urls():
    resolver = get_resolver()
    # Manual recursion is tricky with Django's structures, let's use a simpler printing loop or existing utility if feasible.
    # Actually, simpler:
    
    def print_urls(urlpatterns, prefix=''):
        for pattern in urlpatterns:
            if hasattr(pattern, 'url_patterns'):
                print_urls(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                print(prefix + str(pattern.pattern))

    print_urls(resolver.url_patterns)

if __name__ == '__main__':
    show_urls()
