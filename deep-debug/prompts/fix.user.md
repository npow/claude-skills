Symptom: $symptom
Reproduction: $repro

Promoted hypothesis:
$hypothesis_json

1. Write a failing test that reproduces the exact symptom.
2. Run it — confirm it fails before the fix.
3. Implement ONE focused change addressing the hypothesis mechanism.
4. Re-run the test — confirm it passes.
5. Run the full test suite — confirm no regressions.
Report FIX_APPLIED and TEST_PASSES.
