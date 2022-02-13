from ipaddress import ip_address


def current_ip_address() -> ip_address:
    """
    Gets the current public ip address
    :return: the current public ip address as string
    """
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    address = s.getsockname()[0]
    s.close()
    from ipaddress import ip_address
    return ip_address(address)
