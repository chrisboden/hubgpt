from tools.email_create import execute

with open('real_estate_poem.txt', 'r') as f:
    content = f.read()

result = execute(
    to=['pierre.g@connectedcommercial.com'],
    subject='A Poetic Take on Real Estate',
    html_body=content
)
print(result) 