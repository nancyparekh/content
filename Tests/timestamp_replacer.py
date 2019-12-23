import json
# import urllib
from copy import deepcopy
from typing import List, Union
from mitmproxy import ctx, flow
from time import ctime
from dateutil.parser import parse


class TimestampReplacer:
    def __init__(self):
        self.count = 0
        self.json_keys = set()
        self.query_keys = set()

    def load(self, loader):
        loader.add_option(
            name='keys_to_replace',
            typespec=str,
            default='',
            help='''
            The keys inside a Posted Request's body whose value is a timestamp and needs to be replaced.
            Nested keys whould be written in dot notation.
            '''
        )
        loader.add_option(
            name='detect_timestamps',
            typespec=bool,
            default=False,
            help='''
            Set to True only if recording a mock file. Used to determine which keys need to be replaced in incoming
            request bodies during a mock playback.
            '''
        )
        loader.add_option(
            name='keys_filepath',
            typespec=str,
            default='bad_keys.txt',
            help='''
            The path to the file that contains the problematic keys for the test playbook recording that resides
            in the same directory.
            '''
        )

    def request(self, flow: flow.Flow) -> None:
        self.count += 1
        req = flow.request
        if req.method == 'POST':
            content = req.raw_content.decode()
            json_data = content.startswith('{')
            if json_data:
                content = json.loads(content)

            if ctx.options.detect_timestamps:
                form_urlencoded = 'application/x-www-form-urlencoded' in req.headers.get('content-type', '').lower()
                if form_urlencoded:
                    self.handle_form_urlencoded(flow)
                elif json_data:
                    ctx.log.info('req num: {}\n{}'.format(self.count, content))
                    for problem_key in self.get_problematic_keys(content):
                        self.json_keys.add(problem_key)
            else:
                self.modify_json_body(flow, content)

    def modify_json_body(self, flow: flow.Flow, json_body: dict) -> None:
        '''Modify the json body of a request by replacing any timestampt data with the number of the current request.

        Args:
            flow (flow.Flow): The flow whose request body is to be modified.
            json_body (dict): The request body to modify.
        '''
        original_content = deepcopy(json_body)
        body = json_body
        modified = False
        keys_to_replace = ctx.options.keys_to_replace.split() or []
        ctx.log.info('{}'.format(keys_to_replace))
        for key_path in keys_to_replace:
            body = json_body
            keys = key_path.split('.')
            ctx.log.info('keypath parts: {}'.format(keys))
            lastkey = keys[-1]
            ctx.log.info('lastkey: {}'.format(lastkey))
            skip_key = False
            for k in keys[:-1]:
                if k in body:
                    body = body[k]
                    # ctx.log.info('updated body: {}'.format(body))
                elif isinstance(body, list) and k.isdigit():
                    if int(k) > len(body) - 1:
                        skip_key = True
                        break
                    body = body[int(k)]
                else:
                    skip_key = True
                    break
            if not skip_key:
                if lastkey in body:
                    ctx.log.info('modifying request to "{}"'.format(flow.request.pretty_url))
                    ctx.log.info('original request body:\n{}'.format(json.dumps(original_content, indent=4)))
                    body[lastkey] = self.count
                    modified = True
                elif isinstance(body, list) and lastkey.isdigit() and int(lastkey) <= len(body) - 1:
                    ctx.log.info('modifying request to "{}"'.format(flow.request.pretty_url))
                    ctx.log.info('original request body:\n{}'.format(json.dumps(original_content, indent=4)))
                    body[int(lastkey)] = self.count
                    modified = True
        if modified:
            ctx.log.info('original request body:\n{}'.format(json.dumps(original_content, indent=4)))
            ctx.log.info('modified request body:\n{}'.format(json.dumps(json_body, indent=4)))
            flow.request.raw_content = json.dumps(json_body).encode()

    def handle_form_urlencoded(self, flow: flow.Flow) -> None:
        '''Only used when detecting query parameters to ignore. Updates the query_keys that get written to the
        bad keys file to get ignored.

        Args:
            flow (flow.Flow): The flow whose request is being inspected
        '''
        query_data = flow.request._get_query()
        for key, val in query_data:
            try:
                parse(val)
                self.query_keys.add(key)
            except ValueError:
                pass

    def get_problematic_keys(self, content: dict) -> List[str]:
        '''Given a json request body, return the keys (in dot notation) whose values are potentially timestamp data.

        Args:
            content (dict): The json request body to iterate through and find problematic timestamp data.

        Returns:
            List[str]: A list of keys (in dot notation, e.g. 'query.filter.time' is an example of what could be one
                problematic key) whose values are potentially timestamp data.
        '''
        def travel_dict(obj: Union[dict, list], key_path='') -> List[str]:
            bad_key_paths = []
            if isinstance(obj, dict):
                for key, val in obj.items():
                    sub_key_path = '{}.{}'.format(key_path, key) if key_path else key
                    if isinstance(val, (list, dict)):
                        bad_key_paths.extend(travel_dict(val, sub_key_path))
                    else:
                        is_string = isinstance(val, str)
                        possible_timestamp = isinstance(val, (int, float)) and len(str(val)) >= 8
                        try:
                            if is_string or possible_timestamp:
                                # ctx.log.info('req num: {} keypath: {}'.format(self.count, sub_key_path))
                                for_eval = val
                                if possible_timestamp:
                                    if isinstance(for_eval, float):
                                        digits = str(val).split('.')
                                        for_eval = digits[0]
                                    if len(str(for_eval)) < 14:
                                        parse(ctime(val))
                                    else:
                                        parse(ctime(val / 1000.0))
                                else:
                                    parse(val)
                                # if it continues to the next line that means it successfully parsed the object
                                # and it's some sort of time-related object
                                bad_key_paths.append(sub_key_path)
                        except ValueError:
                            pass
            elif isinstance(obj, list):
                for i, val in enumerate(obj):
                    sub_key_path = '{}.{}'.format(key_path, i) if key_path else i
                    if isinstance(val, (list, dict)):
                        bad_key_paths.extend(travel_dict(val, sub_key_path))
                    else:
                        is_string = isinstance(val, str)
                        possible_timestamp = isinstance(val, (int, float)) and len(str(val)) >= 8
                        try:
                            if is_string or possible_timestamp:
                                # ctx.log.info('req num: {} keypath: {}'.format(self.count, sub_key_path))
                                for_eval = val
                                if possible_timestamp:
                                    if isinstance(for_eval, float):
                                        digits = str(val).split('.')
                                        for_eval = digits[0]
                                    if len(str(for_eval)) < 13:
                                        parse(ctime(val))
                                    else:
                                        parse(ctime(val / 1000.0))
                                else:
                                    parse(val)
                                # if it continues to the next line that means it successfully parsed the object
                                # and it's some sort of time-related object
                                bad_key_paths.append(sub_key_path)
                        except ValueError:
                            pass
            return bad_key_paths
        bad_keys = travel_dict(content)
        return bad_keys

    def done(self):
        if ctx.options.detect_timestamps:
            bad_keys_filepath = ctx.options.keys_filepath
            all_keys = {
                'json_keys': ' '.join(self.json_keys),
                'query_keys': ' '.join(self.query_keys)
            }
            with open(bad_keys_filepath, 'w') as bad_keys_file:
                bad_keys_file.write(json.dumps(all_keys))


addons = [TimestampReplacer()]