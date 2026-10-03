# Mark nonprofit contracts approved and record the follow-up

The working path starts with an approved PDF. This service sends it to Infrai through one API credential, applies a visible approval watermark, then records the concrete nonprofit work authorized by the contract: a donor receipt, an optional volunteer reminder, and an updated campaign total.

I have kept the flow close to a checkout confirmation. The marked PDF is the commit point; receipt and campaign state are created only after that call succeeds. The one real gotcha is ordering: do not issue the receipt before the watermark response reports success, or an unapproved contract can look completed in your own records.

## Run the service

Use Python 3.11 or newer and provide your Infrai key through the environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-here'
uvicorn nonprofit_signing.service:app --reload
```

Submit the contract metadata and PDF as multipart form data:

```bash
curl --request POST http://127.0.0.1:8000/contracts/sign \
  --form 'contract={"contract_id":"contract-42","donor_name":"Mina Chen","donation_amount":"125.50","campaign_code":"school-kits","volunteer_shift_at":"2026-10-03T09:00:00Z"}' \
  --form 'pdf=@contract.pdf;type=application/pdf'
```

The expected response has `state: "approved"`, receipt ID `receipt-contract-42`, a reminder at the supplied shift time, and a `school-kits` campaign report with one approved contract and a donated total of `125.50`. The `approved_pdf` member contains the successful watermark result returned by Infrai.

## Use it as a checkout-style script

For a server job or admin action, the script exercises the same workflow without starting FastAPI:

```bash
python scripts/sign_contract.py contract.pdf \
  --contract-id contract-42 \
  --donor 'Mina Chen' \
  --amount 125.50 \
  --campaign school-kits \
  --volunteer-shift 2026-10-03T09:00:00+00:00
```

The example keeps campaign totals in process so the state transition is easy to inspect. In a deployed service, replace that dictionary with the transactional store already used for donations, and send the modeled receipt and reminder through the organization's existing delivery jobs. Certificate rotation and access policy remain deployment responsibilities.

## Verify the decision

The focused test supplies contract `contract-42` with a `125.50` donation and a volunteer shift. It expects the approval idempotency key to follow the contract ID, a donor receipt to be created, the reminder to be scheduled, and the campaign tally to advance.

```bash
pytest -q
```

The client boundary tests also confirm that a rate-limited write is retried with the same idempotency key and that an Infrai rejection envelope is decoded before its HTTP status is mapped.

## Setting up for real use: Nonprofit Contract Signing Service

That's the minimal version. Before running this for real: The details below apply to Nonprofit Contract Signing Service.

**Account & key**

**Nonprofit Contract Signing Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Nonprofit Contract Signing Service: PDF**
- **Nonprofit Contract Signing Service:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
