class Dotpanel < Formula
  desc "Agent memspace bootstrap and secret injection tools"
  homepage "https://github.com/hioTEC/dotpanel"
  head "https://github.com/hioTEC/dotpanel.git"

  depends_on "age"
  depends_on "git"
  depends_on "jq"

  def install
    system "make", "install", "PREFIX=#{prefix}"
  end

  def caveats
    <<~EOS
      To complete setup, run:
        dot init

      This wires dot and dkey into your shell and renders harness entry files.
      If you already have a memspace repo at ~/.agents, use:
        dot init --no-entry
    EOS
  end

  test do
    system "#{bin}/dot", "version"
    system "#{bin}/dkey", "version"
  end
end
