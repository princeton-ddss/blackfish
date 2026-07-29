import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";
import SortableHeader from "./SortableHeader";

function renderHeader(props) {
  return render(
    <table>
      <thead>
        <tr>
          <SortableHeader
            label="Name"
            sortKey="name"
            activeKey={null}
            direction={null}
            onSort={vi.fn()}
            {...props}
          />
        </tr>
      </thead>
    </table>,
  );
}

describe("SortableHeader", () => {
  test("clicking calls onSort with the column's key", async () => {
    const onSort = vi.fn();
    const { getByRole } = renderHeader({ onSort });
    await userEvent.click(getByRole("button", { name: /name/i }));
    expect(onSort).toHaveBeenCalledWith("name");
  });

  test("reports no sort direction when inactive", () => {
    const { getByRole } = renderHeader({ activeKey: "other", direction: "asc" });
    expect(getByRole("columnheader")).toHaveAttribute("aria-sort", "none");
  });

  test("reflects ascending sort when active", () => {
    const { getByRole } = renderHeader({ activeKey: "name", direction: "asc" });
    expect(getByRole("columnheader")).toHaveAttribute("aria-sort", "ascending");
  });

  test("reflects descending sort when active", () => {
    const { getByRole } = renderHeader({ activeKey: "name", direction: "desc" });
    expect(getByRole("columnheader")).toHaveAttribute("aria-sort", "descending");
  });
});
