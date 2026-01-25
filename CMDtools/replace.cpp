// replace.cpp - stdin -> stdout replacer
// Usage: replace -in "/" -out "\\"
//
// Reads lines from stdin, replaces all occurrences of IN with OUT, writes to stdout.
// Includes basic unescaping for args so you can pass backslashes reliably.
//
// Notes for Windows:
// - Many shells treat backslash weirdly. If you want a single backslash as output,
//   pass -out "\\" (two characters: backslash+backslash), which unescapes to "\".

#include <iostream>
#include <string>
#include <cctype>

static std::string unescape(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (size_t i = 0; i < s.size(); ++i) {
        char c = s[i];
        if (c == '\\' && i + 1 < s.size()) {
            char n = s[++i];
            switch (n) {
                case 'n':  out.push_back('\n'); break;
                case 'r':  out.push_back('\r'); break;
                case 't':  out.push_back('\t'); break;
                case '\\': out.push_back('\\'); break;
                case '"':  out.push_back('"');  break;
                case '\'': out.push_back('\''); break;
                case '0':  out.push_back('\0'); break;
                default:
                    // Unknown escape: keep the char as-is (dropping the backslash)
                    out.push_back(n);
                    break;
            }
        } else {
            out.push_back(c);
        }
    }
    return out;
}

static void replace_all(std::string& line, const std::string& in, const std::string& out) {
    if (in.empty()) return; // avoid infinite loop
    size_t pos = 0;
    while ((pos = line.find(in, pos)) != std::string::npos) {
        line.replace(pos, in.size(), out);
        pos += out.size();
    }
}

int main(int argc, char* argv[]) {
    std::string in = "";
    std::string out = "";
    bool haveIn = false, haveOut = false;

    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if ((a == "-i" || a == "--in") && i + 1 < argc) {
            in = argv[++i];
            haveIn = true;
        } else if ((a == "-o" || a == "--out") && i + 1 < argc) {
            out = argv[++i];
            haveOut = true;
        } else if (a == "-h" || a == "--help") {
            std::cout <<
                "replace - replace all occurrences of IN with OUT\n"
                "Usage: replace -n IN -o OUT\n"
                "  -i,  --in    Input substring to replace\n"
                "  -o,  --out   Output substring\n"
                "\n"
                "Escapes in arguments are supported: \\\\ \\\" \\n \\r \\t\n"
                "Example (slash to backslash): replace --in \"/\" --out \"\\\\\\\\\"\n";
            return 0;
        }
    }

    if (!haveIn || !haveOut) {
        std::cerr << "replace: missing -in or -out. Try --help.\n";
        return 2;
    }

    // Unescape args so -out "\\" turns into "\" reliably.
    in = unescape(in);
    out = unescape(out);

    std::string line;
    while (std::getline(std::cin, line)) {
        // Strip CR if input is CRLF
        if (!line.empty() && line.back() == '\r') line.pop_back();

        replace_all(line, in, out);
        std::cout << line << "\n";
    }

    return 0;
}
