
import os
from django import template
register = template.Library()

@register.filter
def basename(value):
    return os.path.basename(value)

@register.filter(name='truncate_words')
def truncate_words(value, num):
    return ' '.join(value.split()[:int(num)]) + '...'
