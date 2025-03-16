-- Problem:

-- Given an SQL table containing pairs of integers, write the query to fetch the deduplicated pairs.

-- Solution:

-- 1. Schema: Pairs(A INT, B INT)
-- 2. Create a table with above schema and insert some duplicated values.
-- 3. The duplicate pairs (a, b) and (a, b) can be handled with the help of DISTINCT.
-- 4. To deduplicate (a, b) and (b, a), use LEFT JOIN.

DROP TABLE IF EXISTS Pairs;
CREATE TABLE Pairs(A INT, B INT);
INSERT INTO Pairs VALUES (1, 2), (3, 2), (3,2), (2, 4), (2,1), (5, 6), (4, 2);

SELECT * FROM Pairs;
--     --- ---
--    | A | B |
--     --- ---
--    | 1 | 2 |
--    | 3 | 2 |
--    | 3 | 2 |
--    | 2 | 4 |
--    | 2 | 1 |
--    | 5 | 6 |
--    | 4 | 2 |
--     --- ---

SELECT *
FROM Pairs AS t1 LEFT JOIN Pairs AS t2 
ON t1.A=t2.B AND t1.B=t2.A;
--     --- --- --- ---
--    | A | B | A | B |
--     --- --- --- ---
--    | 1 | 2 | 2 | 1 |
--    | 3 | 2 |   |   |
--    | 3 | 2 |   |   |
--    | 2 | 4 | 4 | 2 |
--    | 2 | 1 | 1 | 2 |
--    | 5 | 6 |   |   |
--    | 4 | 2 | 2 | 4 |
--     --- --- --- ---

SELECT *
FROM Pairs AS t1 LEFT JOIN Pairs AS t2
ON t1.A=t2.B AND t1.B=t2.A 
WHERE t2.A IS NULL OR t1.A < t1.B;
--     --- --- --- ---
--    | A | B | A | B |
--     --- --- --- ---
--    | 1 | 2 | 2 | 1 |
--    | 3 | 2 |   |   |
--    | 3 | 2 |   |   |
--    | 2 | 4 | 4 | 2 |
--    | 5 | 6 |   |   |
--     --- --- --- ---

SELECT t1.A, t1.B
FROM Pairs AS t1 LEFT JOIN Pairs AS t2 
ON t1.A=t2.B AND t1.B=t2.A 
WHERE t2.A IS NULL OR t1.A < t1.B;
--     --- ---
--    | A | B |
--     --- ---
--    | 1 | 2 |
--    | 3 | 2 |
--    | 3 | 2 |
--    | 2 | 4 |
--    | 5 | 6 |
--     --- ---

SELECT DISTINCT t1.A, t1.B
FROM Pairs AS t1 LEFT JOIN Pairs AS t2 
ON t1.A=t2.B AND t1.B=t2.A 
WHERE t2.A IS NULL OR t1.A < t1.B;
--     --- ---
--    | A | B |
--     --- ---
--    | 1 | 2 |
--    | 3 | 2 |
--    | 2 | 4 |
--    | 5 | 6 |
--     --- ---
