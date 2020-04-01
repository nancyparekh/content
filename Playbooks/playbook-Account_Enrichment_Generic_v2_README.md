Enriches accounts using one or more integration.

Supported integrations:
- Active Directory

## Dependencies
This playbook uses the following sub-playbooks, integrations, and scripts.

## Sub-playbooks
This playbook does not use any sub-playbooks.

## Integrations
This playbook does not use any integrations.

## Scripts
* ADGetUser

## Commands
This playbook does not use any commands.

## Playbook Inputs
---

| **Name** | **Description** | **Default Value** | **Source** | **Required** |
| --- | --- | --- | --- | --- |
| Username | The username to enrich. | Username | Account | Optional |

## Playbook Outputs
---

| **Path** | **Description** | **Type** |
| --- | --- | --- |
| Account | The account object. | unknown |
| Account.Type | The account entity type. | string |
| Account.ID | The unique account DN (Distinguished Name). | string |
| Account.Username | The account username. | string |
| Account.Email | The email address associated with the account. | unknown |
| Account.Groups | The groups the account belongs to. | unknown |
| Account.DisplayName | The account display name. | string |
| Account.Manager | The account's manager. | string |

![Account_Enrichment_Generic_v2](https://github.com/demisto/content/blob/1bdd5229392bd86f0cc58265a24df23ee3f7e662/docs/images/playbooks/Account_Enrichment_Generic_v2.png)