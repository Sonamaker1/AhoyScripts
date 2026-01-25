// swap.cpp - stdin -> stdout line formatter
// Usage: swap -d " : " -e
//
// Reads lines from stdin, finds the first occurrence of delimiter,
// and outputs: right + delimiter + left
//
// If -e is provided, trims whitespace around both sides before output.

#include <iostream>
#include <string>
#include <vector>
#include <cctype>

static inline void ltrim_inplace(std::string& s) {
    size_t i = 0;
    while (i < s.size() && std::isspace(static_cast<unsigned char>(s[i]))) i++;
    s.erase(0, i);
}

static inline void rtrim_inplace(std::string& s) {
    if (s.empty()) return;
    size_t i = s.size();
    while (i > 0 && std::isspace(static_cast<unsigned char>(s[i - 1]))) i--;
    s.erase(i);
}

static inline void trim_inplace(std::string& s) {
    ltrim_inplace(s);
    rtrim_inplace(s);
}

int main(int argc, char* argv[]) {
    std::string delim = " : ";
    bool trimEdges = false;

    // Parse args
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        if ((a == "-d" || a == "--delim") && i + 1 < argc) {
            delim = argv[++i];
        } else if (a == "-e" || a == "--edges") {
            trimEdges = true;
        } else if (a == "-h" || a == "--help") {
            std::cout <<
                "swap - swap left/right halves of each line around a delimiter\n"
                "Usage: swap [-d DELIM] [-e]\n"
                "  -d, --delim  Delimiter string (default: \" : \")\n"
                "  -e, --edges  Trim whitespace around both halves\n";
            return 0;
        }
    }

    std::string line;
    while (std::getline(std::cin, line)) {
        // Handle CRLF input cleanly (strip trailing '\r' if present)
        if (!line.empty() && line.back() == '\r') line.pop_back();

        if (delim.empty()) {
            // If someone sets empty delimiter, just echo.
            std::cout << line << "\n";
            continue;
        }

        size_t pos = line.find(delim);
        if (pos == std::string::npos) {
            // No delimiter found, echo line unchanged
            std::cout << line << "\n";
            continue;
        }

        std::string left = line.substr(0, pos);
        std::string right = line.substr(pos + delim.size());

        if (trimEdges) {
            trim_inplace(left);
            trim_inplace(right);
        }

        std::cout << right << delim << left << "\n";
    }

    return 0;
}
