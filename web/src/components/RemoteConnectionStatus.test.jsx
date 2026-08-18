import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi } from "vitest";
import RemoteConnectionStatus from "@/components/RemoteConnectionStatus";

const remoteProfile = { name: "della", schema: "slurm", host: "della.princeton.edu", user: "cs7101" };
const localProfile = { name: "local", schema: "slurm", host: "localhost", user: null };

test("renders nothing for a local profile", () => {
  const { container } = render(
    <RemoteConnectionStatus profile={localProfile} isConnected={true} />
  );
  expect(container.firstChild).toBeNull();
});

test("shows 'Connected to user@host' when connected", () => {
  const { getByText } = render(
    <RemoteConnectionStatus profile={remoteProfile} isConnected={true} />
  );
  expect(getByText("Connected to cs7101@della.princeton.edu")).toBeInTheDocument();
});

test("shows 'Connecting...' when neither connected nor errored", () => {
  const { getByText } = render(
    <RemoteConnectionStatus profile={remoteProfile} isConnected={false} connectionError={null} />
  );
  expect(getByText("Connecting...")).toBeInTheDocument();
});

test("shows 'Disconnected' on a connection error", () => {
  const { getByText } = render(
    <RemoteConnectionStatus
      profile={remoteProfile}
      isConnected={false}
      connectionError={{ message: "boom" }}
    />
  );
  expect(getByText("Disconnected")).toBeInTheDocument();
});

test("reconnect button appears only when disconnected and onReconnect is given", async () => {
  const user = userEvent.setup();
  const onReconnect = vi.fn();

  // Connected: no button even with onReconnect.
  const connected = render(
    <RemoteConnectionStatus
      profile={remoteProfile}
      isConnected={true}
      onReconnect={onReconnect}
    />
  );
  expect(connected.queryByRole("button")).toBeNull();
  connected.unmount();

  // Disconnected with onReconnect: button present and wired.
  const { getByRole } = render(
    <RemoteConnectionStatus
      profile={remoteProfile}
      isConnected={false}
      connectionError={{ message: "boom" }}
      onReconnect={onReconnect}
    />
  );
  await user.click(getByRole("button"));
  expect(onReconnect).toHaveBeenCalledTimes(1);
});

test("no reconnect button when onReconnect is omitted, even when disconnected", () => {
  const { queryByRole } = render(
    <RemoteConnectionStatus
      profile={remoteProfile}
      isConnected={false}
      connectionError={{ message: "boom" }}
    />
  );
  expect(queryByRole("button")).toBeNull();
});
