#!/usr/bin/env python3
#
# Demonstrate tydoc working with maplotlib

# Make sure we will use matplot lib headless:
import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt
from tydoc import *

if __name__=="__main__":
    x1 = np.linspace(0.0, 5.0)
    x2 = np.linspace(0.0, 2.0)

    y1 = np.cos(2 * np.pi * x1) * np.exp(-x1)
    y2 = np.cos(2 * np.pi * x2)

    plt.subplot(2, 1, 1)
    plt.plot(x1, y1, 'o-')
    plt.title('A tale of 2 subplots')
    plt.ylabel('Damped oscillation')

    plt.subplot(2, 1, 2)
    plt.plot(x2, y2, '.-')
    plt.xlabel('time (s)')
    plt.ylabel('Undamped')

    # Make a document and put a plot in it

    doc = tydoc()
    doc.h1("Matplotlib demo")
    doc.p("This demonstrates how you can add ",b("matplotlib"),
          " to your documents")
    doc.insert_matplotlib(plt,dpi=72,pad_inches=0.1)
    doc.p("Pretty neat, eh?")
    doc.save("output.html",imagedir=".")
    doc.save("output.tex")


    
