2. Hardening from maker-checker round 1 (verdict DONE with 5 WARN):
   cosine distance_metric on the vec0 table (scores were flooring at 0;
   live re-smoke now 0.646/0.621 on the EN probe), loop-until-stable
   delimiter strip + regression test (nested-tag bypass reproduced by
   reviewer), None-content guard, max_length on /quotes (2000) and
   /search (500) inputs, sanitized 502 detail (raw LLM output no longer
   echoed; existing test updated to the stricter contract), corpus
   README rewritten to state the true zh composition (500 Tang, single
   author) and the 75 empty-theme entries from 3 failed tagging batches.
   Suite 31 passed. Index rebuilt (cosine), 1000 indexed. Backlog (not
   this loop): corpus diversity rebuild, re-tag failed batches,
   atomicity test.
