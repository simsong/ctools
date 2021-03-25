#!/usr/bin/env python3
"""
tydoc_awsome_demo:

This demo shows how we implement some of the futures of R's awsome table.
For details, see:

https://cran.r-project.org/web/packages/kableExtra/vignettes/awesome_table_in_html.html
"""

import pandas as pd
import latex_tools
import tydoc
import os
import io

URL='https://cran.r-project.org/web/packages/kableExtra/vignettes/awesome_table_in_html.html'

DATA="""car,mpg,cyl,disp,hp,drat,wt
Mazda RX4,21.0,6,160,110,3.90,2.620
Mazda RX4 Wag,21.0,6,160,110,3.90,2.875
Datsun 710,22.8,4,108,93,3.85,2.320
Hornet 4 Drive,21.4,6,258,110,3.08,3.215
Hornet Sportabout,18.7,8,360,175,3.15,3.440
"""
df = pd.read_csv(io.StringIO(DATA))


def awsome_demo(output_file):
    doc = tydoc.html()
    doc.head.add_tag("meta", attrib={"name": "viewport", "content": "width=device-width, initial-scale=1"})
    doc.add_stylesheet("https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css")
    doc.add_script("https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js")
    doc.add_script("https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js")
    container = doc.add_tag("div", {"class": "container-fluid main-container"})
    div = container.add_tag("div", {"class": "toc-content col-xs-12 col-sm-8 col-md-9"})
    div.p("With thanks to ").append(tydoc.TyTag('a', attrib={'href': URL}, text=URL))
    div.h1("Overview")
    div.h1("Getting Started")
    div.pre('import pandas as pd\nimport io\n\nDATA="""' +DATA +'"""\ndf = pd.read_csv(io.StringIO(DATA))\n')
    doc.save(output_file)


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("output_file", help="Where to write the output")
    args = parser.parse_args()

    if os.path.exists(args.output_file):
        raise FileExistsError(f"Whoops! {args.output_file}  already exists")

    awsome_demo(args.output_file)
