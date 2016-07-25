
class IceCandidate(object):
    candidate = None
    sdp_mid = None
    sdp_m_line_index = None

    def __init__(self, candidate, sdp_mid, sdp_m_line_index):
        """
        Create ICE Candidate instance
        :param candidate: <dict>
        :param sdp_mid:  <string>
        :param sdp_m_line_index: <int>
        """
        super(IceCandidate, self).__init__()
        self.candidate = candidate
        self.sdp_mid = sdp_mid
        self.sdp_m_line_index = sdp_m_line_index

    def get_candidate(self):
        """
        Return ICE Candidate
        :return:  <dict> candidate
        """
        return self.candidate

    def set_candidate(self, candidate):
        """
        Update current ICE Candidate to best choice
        :param candidate: <dict> candidate
        :return: <None>
        """
        self.candidate = candidate

    def get_sdp_mid(self):
        """
        Get sdpMid param
        :return: <string> sdpMid
        """
        return self.sdp_mid

    def set_sdp_mid(self, sdp_mid):
        """
        sdpMid Setter
        :param sdp_mid:
        :return: <None>
        """
        self.sdp_mid = sdp_mid

    def get_sdp_m_line_index(self):
        """
        sdpMLineIndex getter
        :return: <int>
        """
        return self.sdp_m_line_index

    def set_sdp_m_line_index(self, sdp_m_line_index):
        """
        sdpMLineIndex setter
        :param sdp_m_line_index: <int>
        :return: <None>
        """
        self.sdp_m_line_index = sdp_m_line_index
