import urllib.request

checks = [
    ('/', 'Executive Dashboard'),
    ('/dashboard', 'Executive Dashboard'),
    ('/products', 'Product Catalog'),
    ('/inventory', 'Store Inventory Management'),
    ('/sales', 'Sales History'),
    ('/restock', 'Inventory Restocking History'),
    ('/analytics', 'Product Movement Analytics'),
    ('/recommendations', 'Rule-Based Inventory Recommendations'),
    ('/reports', 'Analytical Reports'),
    ('/products/1', 'Action Figure'),
    ('/sales/829262', 'Sale Transaction #829262')
]

for path, expected in checks:
    url = f'http://127.0.0.1:5000{path}'
    req = urllib.request.urlopen(url, timeout=15)
    body = req.read().decode('utf-8')
    assert expected in body, f'{path} missing {expected}'
    print(f'OK {path:<16} -> HTTP {req.status}, found "{expected}", length {len(body):,} chars')

print('\nALL 11 PAGE ROUTE CONTENT CHECKS VERIFIED!')
