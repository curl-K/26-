package edu.whpu.reagent.web;

import edu.whpu.reagent.domain.Account;
import edu.whpu.reagent.persistence.CabinetRepository;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

@Service
public class AccountUserDetailsService implements UserDetailsService {

    private final CabinetRepository repository;

    public AccountUserDetailsService(CabinetRepository repository) {
        this.repository = repository;
    }

    @Override
    public UserDetails loadUserByUsername(String username) {
        Account account = repository.findAccountByUsername(username)
                .orElseThrow(() -> new UsernameNotFoundException(username));
        String role = "manager".equals(account.getRole()) ? "MANAGER" : "TAKER";
        return User.withUsername(account.getUsername())
                .password(account.getPasswordHash())
                .roles(role)
                .build();
    }
}
