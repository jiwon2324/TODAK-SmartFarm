# -*- coding: utf-8 -*-
"""
LibreOffice(UNO)로 문서 마무리: Word는 목차·필드를 갱신해 다시 저장하고, Word·PPT 모두 PDF로 내보낸다.
  docker run --rm -v <폴더>:/w todak-office python3 /w/finalize.py <in_dir> <pdf_dir> [파일 ...]
"""
import os
import subprocess
import sys
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(n, v):
    p = PropertyValue()
    p.Name, p.Value = n, v
    return p


def connect():
    subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore",
                      "--accept=socket,host=127.0.0.1,port=2002;urp;"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ctx = uno.getComponentContext()
    res = ctx.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", ctx)
    for _ in range(60):
        try:
            c = res.resolve("uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext")
            return c.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", c)
        except Exception:  # noqa: BLE001
            time.sleep(1)
    raise SystemExit("LibreOffice 연결 실패")


def main():
    src, pdf_dir = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or sorted(f for f in os.listdir(src) if f.endswith((".docx", ".pptx")))
    os.makedirs(pdf_dir, exist_ok=True)
    desk = connect()
    for n in names:
        path = os.path.abspath(os.path.join(src, n))
        url = uno.systemPathToFileUrl(path)
        doc = desk.loadComponentFromURL(url, "_blank", 0, (prop("Hidden", True),))
        if n.endswith(".docx"):
            idx = doc.getDocumentIndexes()
            for i in range(idx.getCount()):
                idx.getByIndex(i).update()
            doc.getTextFields().refresh()
            # 목차 쪽번호가 반영되도록 한 번 더
            for i in range(idx.getCount()):
                idx.getByIndex(i).update()
            doc.storeToURL(url, (prop("FilterName", "MS Word 2007 XML"),))
            flt = "writer_pdf_Export"
        else:
            flt = "impress_pdf_Export"
        out = os.path.join(pdf_dir, os.path.splitext(n)[0] + ("_발표" if n.endswith(".pptx") else "") + ".pdf")
        doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(out)), (prop("FilterName", flt),))
        doc.close(True)
        print("ok", n, flush=True)
    try:
        desk.terminate()
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
