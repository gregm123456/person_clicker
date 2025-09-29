from display import Display

d = Display({})
d.init()
print('driver', bool(d.driver))
try:
    d.draw_scaled_png('/assets/unknown_portrait.png')
    print('draw_scaled_png returned')
except Exception as e:
    print('draw_scaled_png raised:', e)
