# -*- coding: utf-8 -*-
# Copyright: (c) 2021, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from . import errors


def _path(api_path, table, *subpaths):
    return "/".join(api_path + ("table", table) + subpaths)


def _query(original=None):
    original = original or dict()
    original.setdefault("sysparm_exclude_reference_link", "true")
    return original


class TableClient:
    def __init__(self, client, batch_size=1000):
        # 1000 records is default batch size for ServiceNow REST API, so we also use it
        # as a default.
        self.client = client
        self.batch_size = batch_size

    def list_records(self, table, query=None):
        base_query = _query(query)
        base_query["sysparm_limit"] = self.batch_size

        offset = 0
        total = 1  # Dummy value that ensures loop executes at least once
        result = []

        while offset < total:
            response = self.client.get(
                _path(self.client.api_path, table),
                query=dict(base_query, sysparm_offset=offset),
            )

            result.extend(response.json["result"])
            total = int(response.headers["x-total-count"])
            offset += self.batch_size

        return result

    def get_record(self, table, query, must_exist=False):
        records = self.list_records(table, query)

        if len(records) > 1:
            raise errors.ServiceNowError(
                "{0} {1} records match the {2} query.".format(
                    len(records), table, query
                )
            )

        if must_exist and not records:
            raise errors.ServiceNowError(
                "No {0} records match the {1} query.".format(table, query)
            )

        return records[0] if records else None

    def get_record_by_sys_id(self, table, sys_id):
        response = self.client.get(_path(self.client.api_path, table, sys_id))
        record = response.json["result"]

        return record

    def create_record(self, table, payload, check_mode, query=None):
        if check_mode:
            # Approximate the result using the payload.
            return payload

        return self.client.post(
            _path(self.client.api_path, table), payload, query=_query(query)
        ).json["result"]

    def update_record(self, table, record, payload, check_mode, query=None):
        if check_mode:
            # Approximate the result by manually patching the existing state.
            return dict(record, **payload)

        return self.client.patch(
            _path(self.client.api_path, table, record["sys_id"]),
            payload,
            query=_query(query),
        ).json["result"]

    def delete_record(self, table, record, check_mode):
        if not check_mode:
            self.client.delete(_path(self.client.api_path, table, record["sys_id"]))


def find_user(table_client, user_id):
    # TODO: Maybe add a lookup-by-email option too?
    return table_client.get_record("sys_user", dict(user_name=user_id), must_exist=True)


def find_assignment_group(table_client, assignment_id):
    return table_client.get_record(
        "sys_user_group", dict(name=assignment_id), must_exist=True
    )


def find_standard_change_template(table_client, template_name):
    return table_client.get_record(
        "std_change_producer_version",
        dict(name=template_name),
        must_exist=True,
    )


def find_change_request(table_client, change_request_number):
    return table_client.get_record(
        "change_request", dict(number=change_request_number), must_exist=True
    )


def find_configuration_item(table_client, item_name):
    return table_client.get_record("cmdb_ci", dict(name=item_name), must_exist=True)


def find_problem(table_client, problem_number):
    return table_client.get_record(
        "problem", dict(number=problem_number), must_exist=True
    )
