"""Generate the sample study PDFs used by PocketFriend's demo mode.

The content is original text written for this project, so nothing copyrighted
is shipped in the repository. Run this script to rebuild the demo files:

    python data/demo/generate_demo_pdfs.py

Requires PyMuPDF (already in requirements.txt). No internet needed.
"""

from pathlib import Path
from textwrap import dedent

import fitz  # PyMuPDF

DEMO_DIR = Path(__file__).resolve().parent

PAGE_WIDTH, PAGE_HEIGHT = 595, 842  # A4 in points
MARGIN = 55
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN

BODY_SIZE = 12.5
BODY_LEADING = 1.4
HEADING_SIZE = 16


def write_pdf(path: Path, title: str, sections: list[tuple[str, str]]) -> int:
    """Lay out (heading, body) sections into a paginated PDF.

    Each section is drawn as its own text box, which keeps the extracted text
    close to the original paragraph structure.
    """
    doc = fitz.open()
    page = None
    cursor = MARGIN

    def new_page() -> None:
        nonlocal page, cursor
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        cursor = MARGIN

    new_page()

    def place(text: str, size: float, gap_after: float) -> None:
        """Insert one block, starting a new page when it no longer fits."""
        nonlocal cursor
        if cursor >= PAGE_HEIGHT - MARGIN - size * 2:
            new_page()

        box = fitz.Rect(MARGIN, cursor, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN)
        room = page.insert_textbox(
            box, text, fontsize=size, fontname="helv", align=0, lineheight=BODY_LEADING
        )
        if room < 0:
            # PyMuPDF inserts nothing when the text does not fit, so it is safe
            # to retry the same block on a fresh page.
            new_page()
            box = fitz.Rect(MARGIN, cursor, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN)
            room = page.insert_textbox(
                box,
                text,
                fontsize=size,
                fontname="helv",
                align=0,
                lineheight=BODY_LEADING,
            )
            if room < 0:
                # Longer than a whole page: slice it into page-sized pieces.
                for piece in _slice_blocks(text, size):
                    box = fitz.Rect(
                        MARGIN, cursor, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN
                    )
                    room = page.insert_textbox(
                        box, piece, fontsize=size, fontname="helv", lineheight=BODY_LEADING
                    )
                    if room < 0:
                        new_page()
                        box = fitz.Rect(
                            MARGIN, cursor, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN
                        )
                        room = page.insert_textbox(
                            box,
                            piece,
                            fontsize=size,
                            fontname="helv",
                            lineheight=BODY_LEADING,
                        )
                    cursor += (PAGE_HEIGHT - MARGIN) - cursor - room + gap_after
                return
        cursor += (PAGE_HEIGHT - MARGIN) - cursor - room + gap_after

    place(title, HEADING_SIZE + 3, 22)

    for heading, body in sections:
        place(heading, HEADING_SIZE, 10)
        for paragraph in dedent(body).strip().split("\n\n"):
            place(" ".join(paragraph.split()), BODY_SIZE, 15)

    doc.save(str(path))
    pages = doc.page_count
    doc.close()
    return pages


def _slice_blocks(text: str, size: float) -> list[str]:
    """Break a very long block into page-sized slices."""
    words = text.split()
    limit = max(80, int(TEXT_WIDTH / (size * 0.5)))
    pieces = []
    for start in range(0, len(words), limit):
        pieces.append(" ".join(words[start : start + limit]))
    return pieces


# ---------------------------------------------------------------------------
# Demo content (original text written for this project)
# ---------------------------------------------------------------------------

DATABASE_NOTES = [
    (
        "1. Why normalization matters",
        """
        A relation schema is a set of tables and the rules that keep them
        consistent. Before a design can be normalized it has to be a valid
        relation: one where every cell holds a single value, every row is
        identified by a key, and every attribute depends on the key.

        Normalization is the process of restructuring a database so that facts
        are stored once. Duplicate storage is not only wasteful, it creates
        update anomalies. If a student's name is stored on three separate rows,
        changing that name can leave the database in a state where the same
        person has two different names. Deleting the last row of a certain kind
        can delete facts about other kinds. Inserting a new row can be rejected
        because a fact that should not have been in that table is missing.

        The goal is a design where each fact lives in exactly one place, and
        every non-key attribute depends only on the key of its own table.
        """,
    ),
    (
        "2. Functional dependencies",
        """
        A functional dependency is written X -> Y. It means that for any two
        rows in the relation, if the rows agree on all attributes in X then
        they must also agree on all attributes in Y. X is called a determinant
        and Y is called a dependent.

        Some dependencies are trivial, meaning Y is a subset of X. For example
        in (StudentID, StudentName), the dependency StudentID -> StudentName is
        not trivial because StudentName is not part of StudentID.

        Given a relation R with attributes A, B and C, the dependencies
        A -> B and A -> C together imply A -> BC. This is called transitivity of
        functional dependency. Dependency A -> B implies AB -> B, which is
        augmentation. Reflexivity says that any set of attributes determines
        itself.

        A candidate key is a minimal set of attributes that determines all the
        other attributes in the relation. A primary key is the candidate key
        chosen to identify rows.
        """,
    ),
    (
        "3. First, second and third normal form",
        """
        First normal form, written 1NF, requires that every attribute holds a
        single atomic value and that every row is unique. A table that stores a
        comma separated list of phone numbers is not in 1NF. Nested tables break
        1NF as well.

        Second normal form, 2NF, requires 1NF and no partial dependency. A
        partial dependency exists when a non-key attribute depends on only part
        of a composite key. In a relation with the composite key (StudentID,
        CourseID) and the attributes StudentName and Grade, StudentName depends
        on StudentID alone. That is a partial dependency, so the relation is not
        in 2NF.

        To fix 2NF you decompose the relation. Students move into their own
        table keyed by StudentID, and Enrolments keeps (StudentID, CourseID,
        Grade). StudentName now depends on the whole key of Students.

        Third normal form, 3NF, requires 2NF and no transitive dependency of a
        non-key attribute on another non-key attribute. In a relation with
        key (StudentID, CourseID) and attributes CourseID, CourseName and
        InstructorID, the attribute CourseName depends on CourseID, and CourseID
        depends on the key. CourseName is therefore transitively dependent on the
        key, which violates 3NF.

        The short version that is worth memorising for an exam: 1NF removes
        repeating groups, 2NF removes partial dependencies, and 3NF removes
        transitive dependencies.
        """,
    ),
    (
        "4. BCNF and lossless joins",
        """
        Boyce-Codd normal form, BCNF, is stricter than 3NF. In BCNF every
        nontrivial functional dependency X -> Y has X as a superkey. The
        difference between BCNF and 3NF shows up in relations with overlapping
        candidate keys.

        Decomposition should be lossless, which means that joining the
        decomposed relations must return exactly the original rows, never fewer
        and never more. For a binary decomposition into R1 and R2 the
        decomposition is lossless if and only if the intersection R1 and R2
        includes a key of at least one of the relations.

        Decomposition should also be dependency preserving. The dependencies of
        the original relation should be checkable on the decomposed relations
        without joining them back together.
        """,
    ),
    (
        "5. Indexes",
        """
        An index is a data structure that lets the database find rows without
        scanning the whole table. A B-tree index keeps keys sorted and is useful
        for equality and range queries on frequently filtered columns.

        Indexes speed up reads but every index must be updated on every insert,
        delete and update, so writes become slower. Indexes also consume disk
        space. A good strategy is to index columns used in WHERE clauses, join
        conditions and ORDER BY clauses.

        A clustered index determines the physical order of the rows in the
        table, so a table can have at most one. A non-clustered index stores
        pointers back to the rows instead of moving them.
        """,
    ),
    (
        "6. Referential integrity",
        """
        A foreign key references a primary key or candidate key in another
        table, or sometimes in the same table. The rule is that the foreign key
        value must match an existing primary key value, or be null.

        Inserts are checked against the parent table, and deletes or updates of
        the parent key are checked against the child table. Cascading actions
        automate this: ON DELETE CASCADE removes matching child rows, and ON
        DELETE SET NULL sets the foreign key to null instead.
        """,
    ),
]

SQL_REVISION = [
    (
        "1. The shape of a SELECT query",
        """
        SQL is declarative: you describe the result you want, not the steps to
        compute it. A single table query has the form SELECT columns FROM table
        WHERE condition GROUP BY columns HAVING condition ORDER BY columns LIMIT
        count.

        The logical processing order is FROM, then WHERE, then GROUP BY, then
        HAVING, then SELECT, then ORDER BY, then LIMIT. This order matters. An
        alias defined in SELECT cannot be used in WHERE, but it can be used in
        ORDER BY.
        """,
    ),
    (
        "2. Filtering with WHERE",
        """
        WHERE keeps only the rows that satisfy a condition and it is applied
        before grouping. Useful operators are =, <>, <, <=, >, >=, BETWEEN,
        IN, LIKE, IS NULL and EXISTS.

        LIKE supports the wildcards % for any sequence of characters and _
        for a single character. To search for a literal percent sign you escape
        it as \\%.

        The three valued logic of SQL matters. Comparisons with NULL produce
        UNKNOWN, not true or false. WHERE only returns rows where the condition
        is TRUE, so rows where the condition is UNKNOWN are dropped. This is why
        "column <> 'value'" will not find NULLs and you need "column IS NULL OR
        column <> 'value'".
        """,
    ),
    (
        "3. Joins",
        """
        An inner join keeps only the rows that match on both sides. A left outer
        join keeps every row from the left table and adds NULL for unmatched
        right rows, which is the join to use when you want all students even if
        they have not enrolled in any course. A right outer join is the mirror
        image and a full outer join keeps rows from both sides.

        Self joins join a table to itself, usually through a manager_id style
        foreign key. Cross joins produce every combination and are used
        deliberately in some reporting queries.

        Joining more than two tables is best written one join at a time in
        order, and using table aliases keeps the query readable.
        """,
    ),
    (
        "4. Aggregation and grouping",
        """
        Aggregate functions compute one value from many rows: COUNT, SUM, AVG,
        MIN and MAX. COUNT(column) ignores NULL values while COUNT(*) counts
        rows, so they can differ.

        GROUP BY collapses rows that share the same values in the grouping
        columns and applies the aggregate functions to each group. HAVING
        filters those groups after aggregation, and it can reference aggregate
        functions, while WHERE cannot.

        The usual exam question is the one about order of clauses: WHERE is
        applied before grouping and HAVING after, so filtering on an aggregate
        such as HAVING COUNT(*) > 5 cannot be written in WHERE.
        """,
    ),
    (
        "5. Subqueries",
        """
        A subquery is a query nested inside another query. It returns one value,
        one row, or many rows, and that shape decides where it can be used: a
        single value subquery can be compared with =, a multi row subquery needs
        IN, and EXISTS tests whether the subquery returns anything at all.

        Correlated subqueries reference the outer query, which means the inner
        query runs once per outer row. That is convenient to write and often
        slow to execute.
        """,
    ),
    (
        "6. Views and indexes for queries",
        """
        A view is a named query stored in the database. Views can restrict the
        columns a user sees, hide complexity, and present the same data in a
        stable way. Updates through a simple view are allowed, but updates
        through a view that uses aggregation or joins are usually restricted.

        When a query is slow, first check whether the filtered and joined columns
        have indexes. EXPLAIN shows the plan the optimizer chose and whether it
        did a full table scan.
        """,
    ),
]

TRANSACTIONS = [
    (
        "1. What a transaction is",
        """
        A transaction is a group of operations that must succeed or fail as one
        unit. A bank transfer is the standard example: it debits one account
        and credits another. If only the debit is applied the money disappears.

        Transactions are started with BEGIN, committed with COMMIT and undone
        with ROLLBACK. A database may also end a transaction implicitly.
        """,
    ),
    (
        "2. ACID properties",
        """
        Atomicity means all operations in the transaction are completed or none
        are. The database guarantees this with an undo log.

        Consistency means the transaction moves the database from one valid
        state to another valid state, respecting all constraints.

        Isolation means the effect of a transaction is not visible to other
        transactions until it commits. Weak isolation allows anomalies.

        Durability means once a transaction commits, the result survives
        crashes, which is why the database writes to a log and flushes it to
        disk before it reports success.
        """,
    ),
    (
        "3. Schedules and anomalies",
        """
        A schedule is the order in which operations of concurrent transactions
        execute. Serial schedules are correct but slow. Interleaved schedules are
        faster but can produce anomalies.

        A dirty read happens when a transaction reads a value that another
        transaction later rolls back, so the reader acted on data that never
        officially existed. A non-repeatable read happens when a transaction
        reads the same row twice and gets different values because another
        transaction committed in between. A phantom read happens when a
        transaction repeats a range query and sees new rows that match the
        condition. A lost update happens when two transactions read the same
        value and only one of the writes survives.
        """,
    ),
    (
        "4. Isolation levels",
        """
        Read uncommitted allows dirty reads. Read committed prevents dirty reads
        but allows non-repeatable reads. Repeatable read prevents dirty and
        non-repeatable reads but can allow phantoms. Serializable prevents all
        of them and matches serial execution.

        Higher isolation reduces concurrency but keeps the database correct, so
        the practical goal is the weakest level that still prevents the
        anomalies an application cannot tolerate.
        """,
    ),
    (
        "5. Locking, two-phase locking and MVCC",
        """
        Two-phase locking has two phases. In the growing phase a transaction may
        take locks but not release them. In the shrinking phase it may release
        locks but not take new ones. A transaction that follows two-phase
        locking is conflict serializable, and it cannot deadlock only if it is
        also wound wait.

        Shared locks allow several readers and block writers. Exclusive locks
        allow only one transaction. Lock upgrade is the move from shared to
        exclusive, and it can deadlock.

        Multi-version concurrency control, MVCC, is an alternative to locking. It
        keeps several versions of each row and lets each transaction read the
        version that was current when the transaction started, so readers never
        block writers and never see uncommitted changes.
        """,
    ),
    (
        "6. Deadlocks",
        """
        A deadlock is a cycle in which every transaction is waiting for a lock
        held by another transaction in the cycle. Two transactions that each
        lock two rows in opposite order deadlock reliably.

        Deadlocks are detected either by waiting, by timing out, or by building
        a wait-for graph and looking for a cycle. The standard responses are to
        abort one victim transaction so it can be retried, or to prevent
        deadlocks by always acquiring locks in a consistent global order.
        """,
    ),
]


def main() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("Database_Systems_Notes.pdf", "Database Systems - Study Notes", DATABASE_NOTES),
        ("SQL_Revision.pdf", "SQL - Revision Notes", SQL_REVISION),
        ("Transactions.pdf", "Transaction Management - Study Notes", TRANSACTIONS),
    ]
    for name, title, sections in jobs:
        pages = write_pdf(DEMO_DIR / name, title, sections)
        print(f"Wrote {name} ({pages} pages)")


if __name__ == "__main__":
    main()