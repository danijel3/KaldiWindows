import logging

log = logging.getLogger('kaldi')
log.setLevel(logging.DEBUG)
fh = logging.FileHandler('main.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)