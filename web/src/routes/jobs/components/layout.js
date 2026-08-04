// Shared height for the two columns of the jobs page. The left column (jobs or
// results table) and the right column (job details or result preview) start at
// the same y, so giving them the same height makes their bottom edges line up.
// Each column is a flex column: fixed-height header/search rows, and a bordered
// body that flexes to fill whatever is left.
export const COLUMN_HEIGHT = "lg:h-[calc(100vh-8.25rem)]";
