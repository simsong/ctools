#
# pdf_tools
# Simson Garfinkel
# US Census Bureau

import os
import os.path

# https://stackoverflow.com/questions/30481136/pywin32-save-docx-as-pdf
# https://stackoverflow.com/questions/6011115/doc-to-pdf-using-python
def convert_doc_to_pdf(infile):
    """Convert a Word .docx to PDF and stores the original file in a directory called converted.
    Throws an exception if it can't convert.
    """

    import os
    outfile = os.path.splitext(infile)[0] + ".pdf"

    if os.path.exists(outfile):
        if os.path.getmtime(infile) < os.path.getmtime(outfile):
            print("NO CONVERT {}: PDF ALREADY EXISTS".format(infile))
            return

    
    print("CONVERT {} to PDF".format(infile))
    try:
        import sys,os,win32com.client,pywintypes
    except ModuleNotFoundError as e:
        print(e)
        print("Cannot convert {} --- please convert it manually".format(infile))
        raise e

    wdFormatPDF = 17
    in_file = os.path.abspath(infile)
    out_file = os.path.abspath(outfile)
    word = win32com.client.Dispatch("Word.Application")
    try:
        doc = word.Documents.Open(in_file)
    except pywintypes.com_error as e:
        print("")
        print("**** CANNOT CONVERT: {} *****".format(infile))
        print(str(e))
        print("")
        exit(1)
        
    doc.SaveAs(out_file, FileFormat=wdFormatPDF)
    doc.Close()
    word.Quit()

    return outfile


if __name__=="__main__":
    #
    # Command oine to test the conversion
    #
    import sys
    ofn = convert_doc_to_pdf(sys.argv[1])
    print("Converted {} to {}".format(sys.argv[1],ofn))
    exit(0)
    
