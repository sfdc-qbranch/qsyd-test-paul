import urllib.parse

def is_github_url(url):
    # Parse the URL using the urlparse function
    parsed_url = urllib.parse.urlparse(url)

    # Check if the scheme is https and the hostname is github.com
    if parsed_url.scheme == "https" and parsed_url.hostname == "github.com":
        return True
    else:
        return False
    