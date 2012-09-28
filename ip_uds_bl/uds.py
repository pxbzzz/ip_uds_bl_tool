import myutils

class UDS():
    """Unified Diagnostic Services"""
    def __init__(self, cantp):
        self.cantp = cantp
        self.can_tx_rdy = True
        self.active = False
        self.addressAndLengthFormatIdentifier = 0
        self.dataFormatIdentifier = 0
        cantp.event_sink = self.on_rcv_data

    def on_rcv_data(self):
        myutils.debug_print(0x1, 'UDS::on_rcv_data')
        self.data_sink.on_rcv_data()
   
    def TransferData(self, data):
        """ Transfers at the most 4095 bytes of data """
        myutils.debug_print(1, "UDS::TransferData")
        self.blockSequenceCounter = (self.blockSequenceCounter + 1) % 255
        self.cantp.Init()
        uds_data = [0x36, self.blockSequenceCounter]
        uds_data.extend(data)
        self.cantp.xmit(uds_data)

    def RequestDownload(self, address, size):
        myutils.debug_print(1, "UDS::RequestDownload")
        self.cantp.Init()
        self.blockSequenceCounter = 0
        uds_data = [0x34]
        uds_data.extend([self.dataFormatIdentifier, self.addressAndLengthFormatIdentifier])
        uds_data.extend(myutils.long_to_list(address))
        uds_data.extend(myutils.long_to_list(size))
        self.cantp.xmit(uds_data)

    def RequestTransferExit(self):
        myutils.debug_print(1, "UDS::RequestTransferExit")
        self.cantp.init()
        self.cantp.xmit([0x37])

    def RoutineControl(self, routine_control_type, routine_id, op):
        myutils.debug_print(1, "UDS::RoutineControl")
        self.cantp.init()
        uds_data = [0x31]
        uds_data.AppendData([routine_control_type])
        uds_data.AppendData([(routine_id & 0xFF) >> 8])
        uds_data.AppendData([routine_id & 0xFF])
        self.cantp.xmit(uds_data)

