import os
from fontTools.ttLib import TTFont

font_dir = 'assets/fonts'
for fn in sorted(os.listdir(font_dir)):
    if fn.endswith('.ttf'):
        f = TTFont(os.path.join(font_dir, fn))
        name_record = f['name']
        family = name_record.getDebugName(1)
        subfamily = name_record.getDebugName(2)
        full = name_record.getDebugName(4)
        postscript = name_record.getDebugName(6)
        weight = f['OS/2'].usWeightClass if 'OS/2' in f else 'N/A'
        print(f"{fn:28s} | Weight: {weight:<4} | Family: '{family}' | Subfamily: '{subfamily}' | PostScript: '{postscript}'")

