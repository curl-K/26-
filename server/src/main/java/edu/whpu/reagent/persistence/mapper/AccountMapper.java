package edu.whpu.reagent.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import edu.whpu.reagent.domain.Account;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface AccountMapper extends BaseMapper<Account> {

    Account findByUsername(@Param("username") String username);

    int updateAccount(Account account);

    int insertAccount(Account account);
}
