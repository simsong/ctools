#!/usr/bin/env python3
#
# Demonstrate tydoc working with maplotlib

# Make sure we will use matplot lib headless:
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg 

import numpy as np
import matplotlib.pyplot as plt
from tydoc import *
import latex_tools

def demo1():
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
    doc.p(["This demonstrates how you can add ",b("matplotlib"),
           " to your documents"])
    doc.append_matplotlib(plt,dpi=72,pad_inches=0.1)
    doc.p("Pretty neat, eh?")
    doc.save("demo1.html")
    doc.save("demo1.tex")
    doc.save("demo1.md")
    
    # Just for grins, let's also run LaTeX
    latex_tools.run_latex("demo1.tex", delete_tempfiles=True)
    
def demo2():
    doc = tydoc()
    doc.h1("sin(x) graph")
    doc.p("Here is a little graph of sin(x) from 0 to 4π")
    doc.p("A second paragraph")
    x = np.linspace(0, np.pi*4)
    fig = Figure(figsize=(4,2))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.plot(x, np.sin(x))
    doc.append_matplotlib(fig, dpi=72, pad_inches=0.1)
    doc.p("A third paragraph")

    doc.h1("sin(2x) graph")
    doc.p("Here is a little graph of sin(2x) from 0 to π")
    x = np.linspace(0, np.pi)
    fig = Figure(figsize=(4,2))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.plot(x, np.sin(2*x))
    doc.append_matplotlib(fig, dpi=72, pad_inches=0.1)
    doc.save("demo2.html")
    doc.save("demo2.tex")
    doc.save("demo2.md")
    # Just for grins, let's also run LaTeX
    latex_tools.run_latex("demo2.tex", delete_tempfiles=True)

if __name__=="__main__":
    demo1()
    demo2()
