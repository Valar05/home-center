#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

static int connect_abstract(const char *name) {
  int fd = socket(AF_UNIX, SOCK_STREAM, 0);
  if (fd < 0) return -1;
  struct sockaddr_un addr;
  memset(&addr, 0, sizeof(addr));
  addr.sun_family = AF_UNIX;
  size_t n = strlen(name);
  if (n + 1 >= sizeof(addr.sun_path)) {
    errno = ENAMETOOLONG;
    close(fd);
    return -1;
  }
  addr.sun_path[0] = '\0';
  memcpy(addr.sun_path + 1, name, n);
  socklen_t len = (socklen_t)(offsetof(struct sockaddr_un, sun_path) + 1 + n);
  if (connect(fd, (struct sockaddr *)&addr, len) < 0) {
    close(fd);
    return -1;
  }
  return fd;
}

static void proxy_pair(int a, int b) {
  char buf[32768];
  for (;;) {
    fd_set rfds;
    FD_ZERO(&rfds);
    FD_SET(a, &rfds);
    FD_SET(b, &rfds);
    int maxfd = a > b ? a : b;
    int r = select(maxfd + 1, &rfds, NULL, NULL, NULL);
    if (r < 0) {
      if (errno == EINTR) continue;
      break;
    }
    if (FD_ISSET(a, &rfds)) {
      ssize_t n = recv(a, buf, sizeof(buf), 0);
      if (n <= 0) break;
      ssize_t off = 0;
      while (off < n) {
        ssize_t w = send(b, buf + off, (size_t)(n - off), 0);
        if (w <= 0) return;
        off += w;
      }
    }
    if (FD_ISSET(b, &rfds)) {
      ssize_t n = recv(b, buf, sizeof(buf), 0);
      if (n <= 0) break;
      ssize_t off = 0;
      while (off < n) {
        ssize_t w = send(a, buf + off, (size_t)(n - off), 0);
        if (w <= 0) return;
        off += w;
      }
    }
  }
}

int main(int argc, char **argv) {
  int port = argc > 1 ? atoi(argv[1]) : 9222;
  const char *abstract_name = argc > 2 ? argv[2] : "chrome_devtools_remote";
  if (port <= 0 || port > 65535) {
    fprintf(stderr, "invalid port\n");
    return 2;
  }
  signal(SIGCHLD, SIG_IGN);
  int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (listen_fd < 0) { perror("socket"); return 1; }
  int yes = 1;
  setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
  struct sockaddr_in addr;
  memset(&addr, 0, sizeof(addr));
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  addr.sin_port = htons((uint16_t)port);
  if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror("bind"); return 1; }
  if (listen(listen_fd, 16) < 0) { perror("listen"); return 1; }
  printf("chrome_devtools_bridge listening 127.0.0.1:%d -> @%s\n", port, abstract_name);
  fflush(stdout);
  for (;;) {
    int client = accept(listen_fd, NULL, NULL);
    if (client < 0) {
      if (errno == EINTR) continue;
      perror("accept");
      return 1;
    }
    int upstream = connect_abstract(abstract_name);
    if (upstream < 0) {
      perror("connect_abstract");
      close(client);
      continue;
    }
    pid_t pid = fork();
    if (pid == 0) {
      close(listen_fd);
      proxy_pair(client, upstream);
      close(client);
      close(upstream);
      return 0;
    }
    close(client);
    close(upstream);
  }
}
