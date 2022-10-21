import os,sys,glob
from os import path

from win32com import client


# Notes on accessing Powerpoint from Python with COM:
# TODO: Find new links! [Links Found, just have to insert here!]
# http://stackoverflow.com/questions/6337595/python-win32-com-closing-excel-workbook
# http://www.numbergrinder.com/2008/11/closing-excel-using-python/
# http://stackoverflow.com/questions/24023518/using-python-to-autofit-all-columns-of-an-excel-sheet

# FileFormat numbers
format_number = {'.pptx':51,
                 '.ppt':52,
                 '.pdf':57}


#
# Uses Powerpoint to convert to .pptx and to .pdf
# https://stackoverflow.com/questions/16683376/print-chosen-worksheets-in-excel-files-to-pdf-in-python
# https://github.com/mwhit74/excel/blob/master/excel_to_pdf.py
def powerpoint_convert(infile,out_ext):
    if out_ext not in format_number:
        print("Unknown extension '{}': valid extensions: {}".format(out_ext,format_number.keys()))

    infile_fullpath = os.path.abspath(infile)
    (base,in_ext) = os.path.splitext(infile_fullpath)

    powerpoint = None
    if not os.path.isfile(infile_fullpath):
        print("{} does not exist".format(infile_fullpath));
        return False

    outfile    = base+out_ext
    if os.path.exists(outfile):
        print("   {} exists".format(outfile))
        return False

    if in_ext==out_ext:
        return False

    # if in_ext.lower()=='.xml' and not is_xls_xml(infile_fullpath):
    #     return False

    powerpoint = client.DispatchEx("Powerpoint.Application")
    powerpoint.Visible = 0
    powerpoint.DisplayAlerts = False


    print("Opening {}".format(infile_fullpath))
    presentation = powerpoint.Presentations.Open(infile_fullpath)

    if out_ext == '.pdf':
        for slide in presentation.Slides:
            # Don't change the orientation
            # ws.PageSetup.Orientation    = 1     # 1=Portrait, 2=Landscape

            # Set page margins (in points) to .5 inches
            # https://docs.microsoft.com/en-us/office/vba/api/excel.pagesetup.leftmargin

            slide.PageSetup.LeftMargin = 36
            slide.PageSetup.RightMargin = 36
            slide.PageSetup.TopMargin = 36
            slide.PageSetup.BottomMargin = 36

            # Make it fit on one page wide
            slide.PageSetup.FitToPagesWide = 1
            # ws.PageSetup.FitToPagesTall = 1

            # We could limit the print area...
            # ws.PageSetup.PrintArea = 'A1:G50'

    print("{} => {}".format(infile_fullpath,outfile))

    # wb.Worksheets.Sheet()
    try:
        presentation.SaveAs(outfile, FileFormat=format_number[out_ext])
    except Exception as e:
        print("Failed to convert")
        print(str(e))

    if presentation:
        presentation.Close(False)         # May work
        powerpoint.Quit()
    return True


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Convert files to .pptx and .pdf',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("infile")
    parser.add_argument("out_ext")
    args = parser.parse_args()
    if "*" or "?" in args.infile:
        for fn in glob.glob(args.infile):
            powerpoint_convert(fn,args.out_ext)
    else:
        powerpoint_convert(args.infile,args.out_ext)
