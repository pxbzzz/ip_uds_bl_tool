import SRecord
import can_if
import can_tp
import uds
import myutils
import System.Timers

flash_sec_addr = [
    0xA0000000,
    0xA0004000,
    0xA0008000,
    0xA000C000,
    0xA0010000,
    0xA0014000,
    0xA0018000,
    0xA001C000,
    0xA0020000,
    0xA0028000,
    0xA0030000,
    0xA0038000,
    0xA0040000,
    0xA0048000,
    0xA0050000,
    0xA0058000,
    0xA0060000,
    0xA0070000,
    0xA0080000,
    0xA0090000,
    0xA00A0000,
    0xA00C0000,
    0xA00E0000,
    0xA0100000,
    0xA0140000,
    0xA0180000,
    0xA01C0000
]
class MainClass:
    def __init__(self, uds):
        self.states = { 'IDLE'                 : 0, 
                        'START'                : 1, 
                        'UDS_TRANSFER_DATA'    : 2, 
                        'UDS_TRANSFER_EXIT'    : 3, 
                        'UDS_REQUEST_DOWNLOAD' : 4 }
        self.state = self.states['IDLE']
        self.uds = uds
        self.uds.event_sink = self.on_rcv_data

    def on_rcv_data(self):
        if self.state <> self.states['IDLE']:
            self.Task()

    def DownloadS19(self, s19filename):
        """ Download S-Record file """
        s19file = open(s19filename)
        lines = s19file.readlines()
        s19file.close()
        self.sr = SRecord.SRecord()
        self.sr.readrecords(lines)
        if myutils.debug_switch & 0x1 <> 0:
            self.sr.print_chunks()
        data = self.sr.get_data()
        self.srec_idx = 0
        # chunk size is limited to 1024 bytes eventhough 4095 is the protocol limit.        
        self.chunk_size = 1024
        self.state = self.states['UDS_REQUEST_DOWNLOAD']
        self.Task()

    def Task(self):
        assert self.state in self.states.values()

        if self.state == self.states['UDS_REQUEST_DOWNLOAD']:
            self.uds.event_sink = self.on_rcv_data             
            data = self.sr.get_data()            
            assert self.srec_idx < len(data)
            self.uds_data = []
            start_address = data[self.srec_idx][0]
            next_address  = data[self.srec_idx][0]
            # concatenate all contiguous data
            while (self.srec_idx < len(data)) and (data[self.srec_idx][0] == next_address):
                self.uds_data.extend(data[self.srec_idx][1])
                next_address = data[self.srec_idx][0] + len(data[self.srec_idx][1])
                self.srec_idx = self.srec_idx + 1
            if len(self.uds_data) > 0:
                self.uds.RequestDownload(start_address, len(self.uds_data))
                self.chunk_idx = 0
                self.state = self.states['UDS_TRANSFER_DATA']            
            else:
                self.state = self.states['IDLE']
        elif self.state == self.states['UDS_TRANSFER_DATA']:
            self.uds.TransferData(self.uds_data[self.chunk_idx:self.chunk_idx+self.chunk_size])
            self.chunk_idx = self.chunk_idx + self.chunk_size
            if self.chunk_idx >= len(self.uds_data):
                self.state = self.states['UDS_TRANSFER_EXIT']
        elif self.state == self.states['UDS_TRANSFER_EXIT']:
            self.uds.RequestTransferExit()       
            data = self.sr.get_data()                 
            if self.srec_idx < len(data):
                self.state = self.states['UDS_REQUEST_DOWNLOAD']
            else:
                self.state = self.states['IDLE']
            #if (myutils.debug_switch & 0x8000) == 0x8000: # stop on first transfer
            #    self.state = self.states['IDLE']            

    def EraseFlashBock(self, start_block_idx, num_blocks):
        params = myutils.long_to_list(flash_sec_addr[start_block_idx])
        params.append(num_blocks)
        self.uds.RoutineControl(uds.control_type['START'], uds.routines['ERASE_MEMORY'], params) 

    def TransferSomeData(self, target_address, data):
        self.uds.event_sink = self.TransferDataTask
        self.uds_data = data
        self.state = self.states['UDS_TRANSFER_DATA']
        self.uds.RequestDownload(target_address, len(data))                

    def TransferDataTask(self):
        if self.state == self.states['UDS_TRANSFER_DATA']:
            self.uds.TransferData(self.uds_data)
            self.state = self.states['UDS_TRANSFER_EXIT']
        elif self.state == self.states['UDS_TRANSFER_EXIT']:
            self.uds.RequestTransferExit()
            self.state = self.states['IDLE']            
    
"""
Steps:-
1. Download SBL
2. Erase App sectors
3. Download(Flash) App.
"""

canif = can_if.CanIf()
cantp = can_tp.CanTp(canif)
uds   = uds.UDS(cantp)
mc    = MainClass(uds)

mc.DownloadS19(r'C:\p\hgprojects\TC27XSBL\app\bin\AurixSBL.s19')
while (mc.state <> mc.states['IDLE'] and (uds.timedout == False)):
    pass    

#mc.EraseFlashBock(7, 25-7)
#mc.DownloadS19(r'C:\p\hgprojects\TC27XAppBuild\app\bin\AurixApp.s19')

mc.TransferSomeData(flash_sec_addr[8], [1, 2, 3, 4, 5, 6, 7, 8, 9, 0xA, 0xB, 0xC, 0xD, 0xE, 0xF, 0x10, 0x11 ])

#for i in range(2):
#    if mc.state == mc.states['IDLE']:
#        break
#    else:
#        mc.Task()

try:
    while (mc.state <> mc.states['IDLE'] and (uds.timedout == False)):
        pass    
    if mc.state == mc.states['IDLE']:
        print 'Operation sucessfully completed.'
    if uds.timedout == True:
        print "UDS timedout."

finally:
    canif.rx_thread_active = False

raw_input('Press any key to continue ...')
