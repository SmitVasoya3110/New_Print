from flask import Blueprint, copy_current_request_context, request, jsonify
import os
import subprocess
import json
from werkzeug.utils import secure_filename
# from src.constants.constfunctions import 
import PyPDF2 as pypdf
import magic
import time
from flask_mail import Mail, Message
from flask import g
import threading
from flask import current_app as application
from src.constants.constfunctions import A3_BC, A3_C, A4_BC, A4_C, allowed_file

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

MIME = ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword',
        'application/vnd.oasis.opendocument.text-master']

handle_files = Blueprint('handle_files',__name__,url_prefix="/api/v1/files")


@handle_files.post('multiple-files-upload')
def upload_files():
    try:
        if not os.path.exists(application.config['UPLOAD_FOLDER']):
            os.mkdir(application.config["UPLOAD_FOLDER"])
        print("In Upload API")
        fetch_file_start = time.perf_counter()
        # check if the post request has the file part
        size, typ = request.form['docFormat'].split('_')
        page_format = request.form['pageFormat']
        if 'files[]' not in request.files:
            resp = jsonify({'message': 'No file part in the request'})
            resp.status_code = 400
            return resp

        files = request.files.getlist('files[]')
        fetch_file_end = time.perf_counter()
        print("Estimated Time Taken By Fetching files:", fetch_file_end - fetch_file_start)
        num_dict = {'numbers': []}

        check_extension_start = time.perf_counter()
        if False in [allowed_file(file.filename) for file in files]:
            return jsonify({"message": "check your file type", "allowed":list(ALLOWED_EXTENSIONS)}),422
        total_pages = 0
        print("Checking file extension as Taken time:", time.perf_counter()-check_extension_start)

        traverse_files = time.perf_counter()
        for file in files:
            
            filename = secure_filename(file.filename)
            print(file.mimetype)

            if file.mimetype == "application/pdf":
                npath = os.path.join(application.config['UPLOAD_FOLDER'], filename)
                file.save(npath)
                with open(npath, 'rb') as fpath:
                    read_pdf = pypdf.PdfFileReader(fpath)
                    num_pages = read_pdf.getNumPages()
                    num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                    print("NUM DICT +++", num_dict)
                    total_pages += num_pages

            if file.mimetype == "image/jpeg" or file.mimetype == "image/png" or file.mimetype == "image/jpg":
                file.save(os.path.join(application.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
                if 'Total_Images' in num_dict.keys():
                    num_dict['Total_Images'] += 1
                else:
                    num_dict['Total_Images'] = 1
                total_pages += 1

            if file.mimetype in MIME:
                file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
                source = os.path.join(application.config['UPLOAD_FOLDER'], filename)
                destination = application.config['UPLOAD_FOLDER']
                output = subprocess.run(
                    ["libreoffice", '--headless', '--convert-to', 'pdf', source, '--outdir', destination])
                print(output)
                new_dest = os.path.splitext(destination + f'/{filename}')[0] + ".pdf"
                with open(new_dest, 'rb') as fpath:
                    read_pdf = pypdf.PdfFileReader(fpath)
                    num_pages = read_pdf.getNumPages()
                    num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                    print(num_pages)
                    total_pages += num_pages
                print("On Going")
    
        print("Estimated Time Taken By File Traversal and Page Calculation is: ", time.perf_counter()-traverse_files)
        num_dict['Total_Pages'] = total_pages
        if size == "A4" and typ.lower() == 'color':
            num_dict['Total_cost'] = round(A4_C(total_pages), 2)
        if size == "A4" and typ.lower() == 'bw':
            num_dict['Total_cost'] = round(A4_BC(total_pages), 2)
        if size == "A3" and typ.lower() == 'color':
            num_dict['Total_cost'] = round(A3_C(total_pages), 2)
        if size == "A3" and typ.lower() == 'bw':
            num_dict['Total_cost'] = round(A3_BC(total_pages), 2)
        num_dict['page_format'] = page_format
        # if success and errors:
        #     errors['message'] = 'File(s) successfully uploaded'
        #     resp = jsonify({"errors": errors, "number": num_dict})
        #     resp.status_code = 500
        #     return resp

        resp = jsonify({'message': 'Files successfully uploaded', "numbers": num_dict})
        resp.status_code = 201
        return resp
    except Exception as e:
        print(e)
        return {"message": "There was an error"}, 500


@handle_files.post('/file-cart-upload')
def cart_upload():
    @copy_current_request_context
    def travers_file(final_result: list, files: list, size: str, typ: str, side: str, dtime: str , user_id: int=None):
        num_dict = {"numbers":[]}
        total_pages = 0
        print("Thread Started")
        for file in files:
            print(">}>}"*20, file)
            print(file.mimetype)
            filename = typ+"_"+size+"_"+side+"_"+str(dtime)+"_"+secure_filename(file.filename)
            print(filename)
            if file.mimetype == "application/pdf":
                npath = os.path.join(application.config['UPLOAD_FOLDER'], filename)
                file.save(npath)
                with open(npath, 'rb') as fpath:
                    read_pdf = pypdf.PdfFileReader(fpath)
                    num_pages = read_pdf.getNumPages()
                    num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                    print("NUM DICT +++", num_dict)
                    total_pages += num_pages

            if file.mimetype == "image/jpeg" or file.mimetype == "image/png" or file.mimetype == "image/jpg":
                file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
                if 'Total_Images' in num_dict.keys():
                    num_dict['Total_Images'] += 1
                else:
                    num_dict['Total_Images'] = 1
                total_pages += 1

            if file.mimetype in MIME:
                file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
                source = os.path.join(application.config['UPLOAD_FOLDER'], filename)
                destination = application.config['UPLOAD_FOLDER']
                output = subprocess.run(
                    ["libreoffice", '--headless', '--convert-to', 'pdf', source, '--outdir', destination])
                print(output)
                new_dest = os.path.splitext(destination + f'/{filename}')[0] + ".pdf"
                with open(new_dest, 'rb') as fpath:
                    read_pdf = pypdf.PdfFileReader(fpath)
                    num_pages = read_pdf.getNumPages()
                    num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                    print(num_pages)
                    total_pages += num_pages
                print("On Going")

        num_dict['Total_Pages'] = total_pages
        if size == "A4" and typ.lower() == 'color':
            num_dict['Total_cost'] = round(A4_C(total_pages), 2)
        if size == "A4" and typ.lower() == 'bw':
            num_dict['Total_cost'] = round(A4_BC(total_pages), 2)
        if size == "A3" and typ.lower() == 'color':
            num_dict['Total_cost'] = round(A3_C(total_pages), 2)
        if size == "A3" and typ.lower() == 'bw':
            num_dict['Total_cost'] = round(A3_BC(total_pages), 2)
        num_dict['page_format'] = side
        print(num_dict)
        final_result.append(num_dict)


    metadata = json.loads(request.form.get('metadata'))
    meta_data = metadata['metadata']
    # user_id = meta_data['user_id']
    current_tp = str(time.time())
    traverse_files = time.perf_counter()

    thread_list = []
    final_result = []
    for data in meta_data:
        num_dict = {"numbers":[]}
        size, typ = request.form[data['docFormat']].split('_')
        #TODO: check for every attributes and vaule is not null
        #TODO: fetch files and check for extension
        #TODO: Travers files and calculate page numbers and do ohter perfomantion -- done
        #TODO: calculate price and numbers and file details for current iteration and append it to global response
        files = request.files.getlist(data["files"])
        side = request.form.get(data['sides'],"")
        check_extension_start = time.perf_counter()

        if False in [allowed_file(file.filename) for file in files]:
            return jsonify({"message": "check your file type", "allowed":list(ALLOWED_EXTENSIONS)}),422
        print("Checking file extension as Taken time:", time.perf_counter()-check_extension_start)
    
        th = threading.Thread(target=travers_file, args=(final_result, files, size, typ, side, current_tp))
        th.start()
        thread_list.append(th)
    print("Thread started")
    for thread in thread_list:
        thread.join()
    end_traversal = time.perf_counter()
    print(final_result)
    print("Estimated Time Taken By File Traversal and Page Calculation is: ", end_traversal-traverse_files)
    return {"traversl_time": (end_traversal-traverse_files), "final_result":final_result}



mail = Mail(application)

@handle_files.post('send-mail')
def send_mail():
        try:
            @copy_current_request_context
            def send_attachment(order_id: int, files: list, psize: str, side: str, amount: float, receiver: str):
                msg = Message('Order', sender=application.config['MAIL_USERNAME'], recipients=[application.config['ORDER_MAIL']])
                msg.body = f"Order has been received with <order_id:{order_id}> from <{receiver}>"
                fpath = []
                print(files)
                for file in files:
                    file = secure_filename(file)
                    print(file)
                    nme = os.path.join(application.config['UPLOAD_FOLDER'], file)
                    fpath.append(nme)
                    print("Full Path.....=>", (os.path.join(application.config['UPLOAD_FOLDER'], file)))
                    buf = open(nme, 'rb').read()
                    print(magic.from_buffer(buf, mime=True))
                    msg.attach(file, magic.from_buffer(buf, mime=True), buf)
                print("Sending Mail")
                mail.send(msg)
                print("successful sending")
                msg = Message("Customer Receipt", sender=application.config['MAIL_USERNAME'], recipients=[receiver])
                main_ = "Details of the Order Placed:\n\n"
                msg.body = main_ + f"Order Id: {order_id} \n Files: {','.join(files)} \n Price: ${amount} \n type: {psize} \n Sides: {side} "
                mail.send(msg)
                print("to the client")

                for pth in fpath:
                    if os.path.isfile(pth) and os.path.exists(pth):
                        os.remove(pth)
                        continue
                    continue

            req_data = request.get_json()
            order_id: int = req_data.get('order_id')
            files: list = req_data.get('files', [])
            psize: str =  req_data.get('psize', '')
            side: str =  req_data.get('side', '')
            amount: float = req_data.get('amount', 0.0)
            receiver: str = req_data.get('receiver', '')

            threading.Thread(target=send_attachment, args=(order_id, files, psize, side, amount, receiver)).start()
        except Exception as e:
            print(e)
            return {"message": "Internal Server Error"}


