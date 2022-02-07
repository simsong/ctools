import os
import os.path
import sys
import os
import glob
import warnings

class NoExcel(Exception):
    def __init__(self, msg=''):
        Exception.__init__(self, msg)

    def __repr__(self):
        return self.message
    __str__ = __repr__


#import win32api

# Notes on accessing Excel from Python with COM:
# http://stackoverflow.com/questions/6337595/python-win32-com-closing-excel-workbook
# http://www.numbergrinder.com/2008/11/closing-excel-using-python/
# http://stackoverflow.com/questions/24023518/using-python-to-autofit-all-columns-of-an-excel-sheet

# FileFormat numbers
format_number = {'.xlsx': 51,
                 '.xlsm': 52,
                 '.xls': 56,
                 '.xlsb': 50,
                 '.pdf': 57}

def is_xls_xml(infile):
    if os.path.splitext(infile)[1].lower()=='.xml':
        with open(infile, "r") as f:
            lines = f.read(65536).split("\n")[0:5]
            if (len(lines)>3 and
                lines[0].strip()=='<?xml version="1.0"?>' and
                    lines[1].strip()=='<?mso-application progid="Excel.Sheet"?>'):
                return True
    return False


#
# Uses Excel to convert to .xlsx and to .pdf
# https://stackoverflow.com/questions/16683376/print-chosen-worksheets-in-excel-files-to-pdf-in-python
# https://github.com/mwhit74/excel/blob/master/excel_to_pdf.py
def excel_convert(infile, out_ext):
    import win32com.client

    if out_ext not in format_number:
        raise ValueError("Unknown extension '{}': valid extensions: {}".format(out_ext, format_number.keys()))

    infile_fullpath = os.path.abspath(infile)
    (base, in_ext) = os.path.splitext(infile_fullpath)

    wb = None
    if not os.path.isfile(infile_fullpath):
        raise FileNotFoundError(infile_fullpath)

    outfile    = base +out_ext
    if os.path.exists(outfile):
        raise FileExistsError(outfile)

    if in_ext==out_ext:
        raise ValueError(f"Input extension {in_ext} matches output extension {out_ext}")

    if in_ext.lower()=='.xml' and not is_xls_xml(infile_fullpath):
        raise RuntimeError(f"{in_ext} is not an XLS XML file")

    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = 0
    excel.DisplayAlerts = False

    print("Opening {}".format(infile_fullpath))
    wb = excel.Workbooks.Open(infile_fullpath)

    if out_ext == '.pdf':
        for ws in wb.Worksheets:
            ws.Activate()                       # activate this worksheet

            # Autofit the colums
            excel.ActiveSheet.Columns.AutoFit()

            excel.PrintCommunication    = False
            # Don't change the orientation
            # ws.PageSetup.Orientation    = 1     # 1=Portrait, 2=Landscape

            # Set page margins (in points) to .5 inches
            # https://docs.microsoft.com/en-us/office/vba/api/excel.pagesetup.leftmargin

            ws.PageSetup.LeftMargin = 36
            ws.PageSetup.RightMargin = 36
            ws.PageSetup.TopMargin = 36
            ws.PageSetup.BottomMargin = 36

            # Make it fit on one page wide
            ws.PageSetup.FitToPagesWide = 1
            # ws.PageSetup.FitToPagesTall = 1

            # We could limit the print area...
            # ws.PageSetup.PrintArea = 'A1:G50'

            excel.PrintCommunication    = True

    print("{} => {}".format(infile_fullpath, outfile))

    # Select all worksheets for the save process
    wb.Worksheets.Select()
    wb.SaveAs(outfile, FileFormat=format_number[out_ext])
    wb.Close(False)         # May work
    # Excel quits properly for PDF conversion but not other types
    excel.Quit()
    return True


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Convert files to .xlsx and .pdf',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("infile")
    parser.add_argument("out_ext")
    args = parser.parse_args()
    if "*" or "?" in args.infile:
        for fn in glob.glob(args.infile):
            excel_convert(fn, args.out_ext)
    else:
        excel_convert(args.infile, args.out_ext)
